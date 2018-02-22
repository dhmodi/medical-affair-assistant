#!/usr/bin/env python

from __future__ import print_function
from future.standard_library import install_aliases
import cx_Oracle
install_aliases()
import json
import os
import sys
import pandas as pd
sys.path.append('cognitiveSQL')
from flask import Flask
from flask import request
from flask import make_response
from flask import url_for, redirect
from flask_socketio import SocketIO, send, emit
import subprocess
import cognitiveSQL.Database as Database
import cognitiveSQL.LangConfig as LangConfig
import cognitiveSQL.Parser as Parser
import cognitiveSQL.Thesaurus as Thesaurus
import cognitiveSQL.StopwordFilter as StopwordFilter
from cognitiveSQL.HashMap import hashMap_columns
from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import datetime
import math
import psycopg2
import apiai
import requests
# Flask app should start in global layout
app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)

parser = ""
baseUrl = "https://api.dialogflow.com/v1/query?v=20170712"
accessToken = "66ad5ee869a34d3593181c0f9ff0922c"

# @app.route('/')
# def index():
#     return redirect(url_for('static_url', filename='index.html'))

def select_inquiry_response(prod_name, columnName,indication):
    try:
        url = urlparse(
            "postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
        print(url.path[1:])
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cur = conn.cursor()
        sql = "select " + columnName + " from public.inquiry_response where product_name = '%s' and indication = '%s' limit %s" %(prod_name,indication,1)
        cur.execute(sql)
        row = cur.fetchone()
        #print(row[1])
        #print("The number of parts: ", cur.rowcount)
        cur.close()
        return row
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


def insert_inquiry_details(division,country,master_prod,inquiry,customer_type,customer_channel,facilitated_unfacilitated,case_create_dt,case_clsd_dt,resp_id,response):

    sql = "INSERT INTO public.inquiry_data (Division,Country,Master_Prod ,Inquiry,Customer_Type,Customer_channel,Facilitated_Unfacilitated,Case_Create_Date,Case_Closed_Date,Resp_Id,Response) VALUES(%s, %s, %s, %s, %s, %s,%s,%s, %s, %s, %s)";

    try:
        # read database configuration
        #params = config()
        # connect to the PostgreSQL database
        url = urlparse(
            "postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
        #print(url.path[1:])
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.execute(sql,(division,country,master_prod,inquiry,customer_type,customer_channel,facilitated_unfacilitated,case_create_dt,case_clsd_dt,resp_id,response))
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

@app.route('/speech')
def speech():
    return redirect(url_for('static', filename='speech.html'))

@app.route('/visualization')
def visualization():
    return redirect(url_for('static', filename='visualization.html'))

# @app.route('/inventory')
# def inventory():
#     return redirect(url_for('static_url', filename='index.html'))

@app.route('/emailAffair', methods=['POST'])
def emailAffair():
    req = request.get_json(silent=True, force=True)
    print("Request")
    action = ""
    speech = ""
    productName = ""
    print(json.dumps(req, indent=4))
    if (req.get("inquiryQuestion") is not None or req.get("inquiryQuestion") != ""):
        print(req.get("age"))
        if req.get("age") == "":
            age = "0"
        else:
            age = req.get("age")

        if (req.get("location") == ""):
            location = "India"
        else:
            location = req.get("location")

        if (req.get("profession") == ""):
            profession = "Doc"
        else:
            profession = req.get("profession")

        values = json.dumps({
                "lang": "en",
                "query": req.get("inquiryQuestion")+" "+age+" "+profession+" "+location,
                "sessionId": "12345",
                "timezone": "America/New_York"
            })
        headers ={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer '+accessToken
                }
        res = json.loads(requests.post(url=baseUrl, data=values,headers=headers).text)
        print(res.get("result").get("fulfillment").get("speech"))
        action = res.get("result").get("action")
        speech = res.get("result").get("fulfillment").get("speech")
        productName = res.get("result").get("parameters").get("ProductName")

    res = json.dumps({
            "category": action,
            "response": speech,
            "ProductName": productName
        }, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/medicalAffair', methods=['POST'])
def medicalAffair():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):


    is_Alexa_json = False
    is_Apiai_json = False
    if "request" in req:
        is_Alexa_json = True
    if "result" in req:
        is_Apiai_json = True

    global OutMap

    if is_Apiai_json == True:
        if (req.get("result").get("action") == "ProdAppearance" or req.get("result").get(
                "action") == "ProdAvailability" or req.get("result").get("action") == "ProdGenericAvailability" or req.get("result").get("action") == "ProdDescription" or req.get("result").get("action") == "ProdWork" or req.get("result").get("action") == "ProdSideEffect" or req.get("result").get("action") == "ProdDosageReco"):
            print(req.get("result").get("action"))
            actionIncompleteStatus = req.get("result").get("actionIncomplete")
            print(actionIncompleteStatus)
            fac_unfac = ""
            master_prod = ""
            response = ""
            status = False
            if actionIncompleteStatus:
                print("Skipping")
            else:
                print("Accepted")
                if ((req.get("result").get("action") is not None) or (
                        req.get("result").get("parameters").get("ProductName") is not None) or (
                        req.get("result").get("parameters").get("UserRegion") is not None) or (
                        req.get("result").get("UserAge").get("amount") is not None) or (
                        req.get("result").get("UserAge").get("unit") is not None)):
                    if (req.get("result").get("action") == "ProdAppearance"):
                        print("ProdApperance")
                        Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),
                                                                "Apperance",req.get("result").get("parameters").get("ProdIndication"))
                        if Prod_Response != None:
                            status = True;
                            if len(Prod_Response[0]) > 0:
                                fac_unfac = 'Facilitated'
                                response = Prod_Response[0] + "Was this information useful?"
                            else:
                                fac_unfac = 'UnFacilitated'
                                response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                            master_prod = 'Product Appearance'
                            # response = Prod_Response[0]
                        else:
                            status = False
                            fac_unfac = 'Unfacilitated'
                    elif (req.get("result").get("action") == "ProdAvailability"):
                        print("ProdAvailability")
                        Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),
                                                                "Availability",req.get("result").get("parameters").get("ProdIndication"))
                        if Prod_Response != None:
                            status = True;
                            if len(Prod_Response[0]) > 0:
                                fac_unfac = 'Facilitated'
                                response = Prod_Response[0] + "Was this information useful?"
                            else:
                                fac_unfac = 'UnFacilitated'
                                response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                            master_prod = 'Product Availability'
                        else:
                            status = False;
                            fac_unfac = 'Unfacilitated'
                    elif (req.get("result").get("action") == "ProdGenericAvailability"):
                        print("ProdGenericAvailable")
                        Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),
                                                                "Generic_Availables",req.get("result").get("parameters").get("ProdIndication"))
                        if Prod_Response != None:
                            status = True
                            if len(Prod_Response[0]) > 0:
                                fac_unfac = 'Facilitated'
                                response = Prod_Response[0] + "Was this information useful?"
                            else:
                                fac_unfac = 'UnFacilitated'
                                response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                            master_prod = 'Product Generic Availability'
                        else:
                            status = False
                            fac_unfac = 'Unfacilitated'
                    elif (req.get("result").get("action") == "ProdDescription"):
                            print("ProdDescription")
                            Prod_Response = select_inquiry_response(
                                req.get("result").get("parameters").get("ProductName"),
                                "description",req.get("result").get("parameters").get("ProdIndication"))
                            if Prod_Response != None:
                                status = True
                                if len(Prod_Response[0]) > 0:
                                    fac_unfac = 'Facilitated'
                                    response = Prod_Response[0] + "Was this information useful?"
                                else:
                                    fac_unfac = 'UnFacilitated'
                                    response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                                master_prod = 'Product Generic Availability'
                            else:
                                status = False
                                fac_unfac = 'Unfacilitated'
                            # Default else
                    elif (req.get("result").get("action") == "ProdWork"):
                            print("ProdWork")
                            Prod_Response = select_inquiry_response(
                                req.get("result").get("parameters").get("ProductName"),
                                "how_does_it_to_work",req.get("result").get("parameters").get("ProdIndication"))
                            if Prod_Response != None:
                                status = True
                                if len(Prod_Response[0]) > 0:
                                    fac_unfac = 'Facilitated'
                                    response = Prod_Response[0] + "Was this information useful?"
                                else:
                                    fac_unfac = 'UnFacilitated'
                                    response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                                master_prod = 'Product Generic Availability'
                            else:
                                status = False
                                fac_unfac = 'Unfacilitated'
                            # Default else
                    elif (req.get("result").get("action") == "ProdSideEffect"):
                            print("ProdSideEffect")
                            Prod_Response = select_inquiry_response(
                                req.get("result").get("parameters").get("ProductName"),
                                "sideeffect",req.get("result").get("parameters").get("ProdIndication"))
                            if Prod_Response != None:
                                status = True
                                if len(Prod_Response[0]) > 0:
                                    fac_unfac = 'Facilitated'
                                    response = Prod_Response[0] + "Was this information useful?"
                                else:
                                    fac_unfac = 'UnFacilitated'
                                    response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                                master_prod = 'Product Generic Availability'
                            else:
                                status = False
                                fac_unfac = 'Unfacilitated'
                            # Default else
                    elif (req.get("result").get("action") == "ProdDosageReco"):
                            print("ProdDosageReco")
                            Prod_Response = select_inquiry_response(
                                req.get("result").get("parameters").get("ProductName"),
                                "number_of_times_reco_tot_start_dosage",req.get("result").get("parameters").get("ProdIndication"))
                            if Prod_Response != None:
                                status = True
                                if len(Prod_Response[0]) > 0:
                                    fac_unfac = 'Facilitated'
                                    response = Prod_Response[0] + "Was this information useful?"
                                else:
                                    fac_unfac = 'UnFacilitated'
                                    response = "Your query will be sent to the concerned SME Team and they will get in touch with you. Please provide your Mail ID."
                                master_prod = 'Product Generic Availability'
                            else:
                                status = False
                                fac_unfac = 'Unfacilitated'
                            # Default else
                    else:
                        status = False

                # final if Statement
                if status:
                    insert_inquiry_details('Amer',
                                           req.get("result").get("parameters").get("UserRegion"),
                                           req.get("result").get("parameters").get("ProductName"),
                                           master_prod,
                                           req.get("result").get("UserProfession"),
                                           req.get("result").get("source"),
                                           fac_unfac,
                                           datetime.datetime.utcnow(),
                                           datetime.datetime.utcnow(),
                                           0,
                                           response
                                           )
                    return {
                        "speech": response,
                        "displayText": response,
                        # "data": data,
                        # "contextOut": [],
                        "AppId":1,
                        "source": req.get("result").get("source")
                    }
                else:
                    # insert_inquiry_details('Amer',
                    #                        req.get("result").get("parameters").get("UserRegion"),
                    #                        req.get("result").get("parameters").get("ProductName"),
                    #                        'Data Not Found',
                    #                        req.get("result").get("UserProfession"),
                    #                        req.get("result").get("source"),
                    #                        'Unfacilitated',
                    #                        datetime.datetime.utcnow(),
                    #                        datetime.datetime.utcnow(),
                    #                        0,
                    #                        "Details not found"
                    #                        )
                    return {
                        "speech": "Details Not found",
                        "displayText": "Details Not found",
                        # "data": data,
                        # "contextOut": [],
                        "source": req.get("result").get("source")
                    }

        elif (req.get("result").get("action") == "medical.search"):
            url = urlparse("postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
            print (url.path[1:])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            print("Medical Search")
            incoming_query = req.get("result").get("resolvedQuery")
            hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'

            OutMap = {}
            (input_sentence, OutMap) = hashMap_columns(str(incoming_query).lower(), hashColumn_csv, OutMap)
            print(input_sentence)
            print(OutMap)
            # print(query for query in queries)
            queries = parser.parse_sentence(input_sentence)
            queryString = ""
            table = ""
            for query in queries:
                table = query.get_from().get_table()
                columns = query.get_select().get_columns()
                conditions = query.get_where().get_conditions()
                queryString = queryString + str(query)
            print("table:")
            print(table)
            # print(list(columns))
            print(columns)
            print(columns[0])
            # print(columns[1])
            # xAxis = columns[0][0].split('.')[1]
            # yAxis = columns[1][0].split('.')[1]
            print(queryString)
            cur = conn.cursor()
            cur.execute(queryString)
            rows = cur.fetchall()
            cur.close()
            conn.close()

            # outText = ', '.join(str(x) for x in rows[0])
            # outText = ', '.join(str(element).split(".")[0] for row in rows for element in row)
            count = 0
            if len(conditions) != 0:
                whereColumn = []
                whereValue = []
                for i in range(0, len(conditions)):
                    print(conditions[i][1].get_column().rsplit('.', 1)[1].rstrip(')'))
                    print(conditions[i][1].get_value().strip("'"))
                    whereColumn.append(conditions[i][1].get_column().rsplit('.', 1)[1].rstrip(')'))

                    if " MAX" not in conditions[i][1].get_value() and " MIN" not in conditions[i][1].get_value():
                        whereValue.append(conditions[i][1].get_value().strip("'"))
                    else:
                        if " MAX" in conditions[i][1].get_value():
                            whereValue.append("max")
                        else:
                            whereValue.append("min")
            outText = "The "
            # if len(rows)==1:
            print("length of rows")
            print(len(rows))
            print(rows)

            if len(rows) == 1:
                for row in rows:
                    print(count)
                    isLast = len(row)
                    for element in row:
                        isLast = isLast - 1
                        value = str(element).split(".")[0]

                        if (columns[count][0] is not None):
                            # print(columns)
                            column = columns[count][0].split('.')[1]
                            print(column)
                        operation = columns[count][1]

                        if (operation is None):
                            print("The Operation is None")
                            column = OutMap.get(column)
                            whereValue1 = OutMap.get(whereValue[0]) if (OutMap.get(whereValue[0])) else whereValue[0]
                            whereColumn1 = OutMap.get(whereColumn[0]) if (OutMap.get(whereColumn[0])) else whereColumn[
                                0]
                            try:
                                print(whereValue[1])
                                print(whereColumn[1])
                                whereValue2 = OutMap.get(whereValue[1]) if (OutMap.get(whereValue[1])) else whereValue[
                                    1]
                                whereColumn2 = OutMap.get(whereColumn[1]) if (OutMap.get(whereColumn[1])) else \
                                whereColumn[1]
                                if 'whereColumn' in locals():
                                    # outText = str(column) + " " + value + " in the " + str(whereColumn1) + " " + str(
                                    #     whereValue1) + " has " + str(whereValue2) + " " + str(whereColumn2)
                                    outText = "The " + str(column) + " for " + str(whereColumn1) + " " + str(
                                        whereValue1) + " in " + str(whereColumn2) + " is " + value + "%"
                                else:
                                    outText = outText + str(column) + " is " + value

                            except IndexError:
                                if 'whereColumn' in locals():
                                    outText = str(column) + " " + value + " has " + str(whereValue1) + " " + str(
                                        whereColumn1)
                                else:
                                    outText = outText + str(column) + " is " + value

                        elif (operation is "COUNT"):
                            table = OutMap.get(table)
                            print("The Operation is " + str(operation))
                            if 'whereColumn' in locals():
                                outText = "There are " + value + " " + str(table) + " with " + str(
                                    whereValue[0]) + " " + str(whereColumn[0])
                            else:
                                outText = "There are " + value + " " + str(table)
                        else:
                            # operation = OutMap.get(str(operation).lower())
                            column = OutMap.get(column)
                            # whereValue = OutMap.get(whereValue)
                            print("The Operation is " + str(operation))
                            if 'whereColumn' in locals():
                                outText = "There are " + value + " " + str(column) + " in " + str(
                                    whereValue[0]) + " for " + str(whereValue[1]) + " " + str(whereColumn[1])
                            else:
                                if "what" in incoming_query:
                                    outText = "The " + OutMap.get(str(operation).lower()).lower() + " " + str(
                                        column) + " is " + value
                                elif "how" in incoming_query:
                                    outText = "There are " + value + " " + str(column)

                        if (isLast is not 0):
                            outText = outText + " and the "
                            count = count + 1

            else:
                print(whereColumn)
                print(whereValue)
                print(table)
                print(columns[1][0])
                column = columns[0][0].split('.')[1]
                column2 = columns[1][0].split('.')[1]
                sent_label = OutMap[column]
                sent_value = OutMap[column2]

                print(sent_label)
                outText = whereColumn[0] + " " + OutMap[whereValue[0]] + " has the following " + sent_label + ": "
                print(rows)
                print(columns)
                print(len(columns))

                no_of_rows = len(rows)
                counter = no_of_rows
                for row in rows:
                    counter = counter - 1
                    label = row[0]
                    value = row[1]
                    if counter != 0:
                        outText = outText + str(column) + " " + str(label) + " has " + str(column2) + " of " + str(
                            value) + ", "
                    else:
                        outText = outText + "whereas " + str(column) + " " + str(label) + " has " + str(
                            column2) + " of " + str(value)
                # outText = "The"
            print(outText)

            return {
                "speech": outText,
                "displayText": outText,
                # "data": data,
                # "contextOut": [],
                "source": "Dhaval"
            }
        elif (req.get("result").get("action") == "medical.visualization"):
            url = urlparse("postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
            print (url.path[1:])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            print("Medical Visualization")
            # chartType = "line"
            incoming_query = req.get("result").get("resolvedQuery")
            print(incoming_query)
            chartType = req.get("result").get("parameters").get("chart-type")
            # if (chartType == "bar"):
            #     chartType = "bar"
            # else:
            #     chartType = "line"

            hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'
            OutMap = {}
            (input_sentence, OutMap) = hashMap_columns(str(incoming_query).lower(), hashColumn_csv, OutMap)
            print(OutMap)
            print(input_sentence)
            queries = parser.parse_sentence(input_sentence)
            # queries = parser.parse_sentence(incoming_query)
            # print(query for query in queries)
            queryString = ""
            table = ""
            for query in queries:
                table = query.get_from().get_table()
                columns = query.get_select().get_columns()
                conditions = query.get_where().get_conditions()
                queryString = queryString + str(query)

            # chartType = req.get("result").get("parameters").get("chart-type")
            # print(chartType)

            print(queryString)
            cur = conn.cursor()
            cur.execute(queryString)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            print(rows)
            print(list(columns))

            if len(columns) <= 2:
                xAxis = columns[0][0].split('.')[1]
                yAxis = columns[1][0].split('.')[1]
                xAxis = OutMap.get(xAxis) if OutMap.get(xAxis) else xAxis
                yAxis = OutMap.get(yAxis) if OutMap.get(yAxis) else yAxis
                print(xAxis)
                print(yAxis)
                print(chartType)
                df = pd.DataFrame(list(rows), columns=["label", "value"])
                df['value'] = df['value'].fillna(0)
                agg_df = df.groupby(['label'], as_index=False).agg({"value": "sum"})
                maxRecord = agg_df.ix[agg_df['value'].idxmax()].to_frame().T
                maxValue = agg_df['value'].max()
                print(maxRecord)
                print(maxValue)

                agg_df = agg_df.reset_index()
                minRecord = agg_df.ix[agg_df['value'].idxmin()].to_frame().T
                minValue = agg_df['value'].min()
                print(minRecord)
                print(minValue)

                agg_df['label'] = agg_df['label'].astype('str')
                agg_df['value'] = agg_df['value'].astype('str')

                agg_df.drop(columns=['index'], inplace=True)
                agg_df.reset_index(drop=True, inplace=True)
                print("agg_df:")
                print(agg_df)

                if chartType == 'geochart':
                    for id, cn in enumerate(agg_df['label']):
                        if cn == 'UK':
                            agg_df['label'][id] = 'GB'

                chartData = agg_df.to_json(orient='records')
                # chartData = [{"label": str(row[0]), "value": str(row[1])} for row in rows]
                print("agg_df:")
                print(agg_df)
                print("chartData:")
                print(chartData)
                # chartData = json.dumps(chartData)
                # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"xAxis", "yAxisName":"yAxis","source":[ { "label": "Mon", "value": "15123" }, { "label": "Tue", "value": "14233" }, { "label": "Wed", "value": "23507" }, { "label": "Thu", "value": "9110" }, { "label": "Fri", "value": "15529" }, { "label": "Sat", "value": "20803" }, { "label": "Sun", "value": "19202" } ]}]'
                final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

                print(final_json)

                socketio.emit('chartgoogledata', final_json)
                outText = "The " + xAxis + " " + str(
                    maxRecord['label'].values[0]) + " has maximum " + yAxis + " of " + str(
                    maxValue) + " while the " + xAxis + " " + str(
                    minRecord['label'].values[0]) + " has minimum " + yAxis + " of " + str(
                    minValue) + ". Refer to the screen for more details."
                # outText = "Refer to the screen for more details."
                print(outText)
                return {
                    "speech": outText,
                    "displayText": outText,
                    # "data": data,
                    # "contextOut": [],
                    "source": "Dhaval"
                }

            else:
                xAxis = columns[0][0].split('.')[1]
                yAxis = columns[1][0].split('.')[1]
                zAxis = columns[2][0].split('.')[1]
                xAxis = OutMap.get(xAxis) if OutMap.get(xAxis) else xAxis
                yAxis = OutMap.get(yAxis) if OutMap.get(yAxis) else yAxis
                zAxis = OutMap.get(zAxis) if OutMap.get(zAxis) else zAxis

                print(xAxis)
                print(yAxis)
                print(zAxis)
                print(chartType)

                df = pd.DataFrame(list(rows), columns=["datatype", "country", "dq_score"])
                df['dq_score'] = df['dq_score'].fillna(0)
                # print(df)

                agg_df = df.groupby(['datatype', 'country'], as_index=False)['dq_score'].sum()
                print(agg_df)

                maxRecord = agg_df.ix[agg_df['dq_score'].idxmax()].to_frame().T
                agg_df = agg_df.reset_index()
                minRecord = agg_df.ix[agg_df['dq_score'].idxmin()].to_frame().T
                print(maxRecord)
                print(minRecord)
                agg_df['datatype'] = agg_df['datatype'].astype('str')
                agg_df['country'] = agg_df['country'].astype('str')
                agg_df.drop(columns=['index'], inplace=True)
                # agg_df.reset_index(drop=True, inplace=True)
                print("agg_df:")
                print(agg_df)

                pd.options.mode.chained_assignment = None

                for i in range(len(agg_df['datatype'])):
                    agg_df['datatype'][i] = agg_df['datatype'][i].replace(" ", "_")

                print(agg_df)

                unique_countries = set(agg_df['country'])
                unique_countries = list(unique_countries)

                unique_datatypes = set(agg_df['datatype'])
                unique_datatypes = list(unique_datatypes)

                df = agg_df
                df2 = pd.DataFrame(columns=['country', 'values'])
                df2['country'] = ['' for i in range(len(unique_countries))]

                for idx, cn in enumerate(unique_countries):
                    df2['country'][idx] = cn
                    df2['values'][idx] = {}

                for ind, val in enumerate(df2['values']):
                    for idx, dtyp in enumerate(unique_datatypes):
                        df2['values'][ind][dtyp] = 0

                for ind, cn in enumerate(df['country']):
                    for i, c in enumerate(df2['country']):
                        dat = df['datatype'][ind]
                        dqs = df['dq_score'][ind]
                        if cn == c:
                            df2['values'][i][dat] = dqs

                print(df2)

                agg_df = df2

                chartData = agg_df.to_json(orient='records')
                # chartData = [{"label": str(row[0]), "value": str(row[1])} for row in rows]
                print("agg_df:")
                print(agg_df)
                print("chartData:")
                print(chartData)
                # chartData = json.dumps(chartData)
                # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"xAxis", "yAxisName":"yAxis","source":[ { "label": "Mon", "value": "15123" }, { "label": "Tue", "value": "14233" }, { "label": "Wed", "value": "23507" }, { "label": "Thu", "value": "9110" }, { "label": "Fri", "value": "15529" }, { "label": "Sat", "value": "20803" }, { "label": "Sun", "value": "19202" } ]}]'
                final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

                print(final_json)

                socketio.emit('chartgoogledata', final_json)
                # outText = "The " + xAxis + " " + str(
                #     maxRecord['label'].values[0]) + " has maximum " + yAxis + " while the " + xAxis + " " + str(
                #     minRecord['label'].values[0]) + " has minimum " + yAxis + ". Refer to the screen for more details."
                outText = "Refer to the screen for more details."
                print(outText)
                return {
                    "speech": outText,
                    "displayText": outText,
                    # "data": data,
                    # "contextOut": [],
                    "source": "Dhaval"
                }

    elif is_Alexa_json == True:
        if (req.get("request").get("intent").get("name") == "medicalsearch"):
            url = urlparse("postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
            print (url.path[1:])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )

            print("Medical Search")
            incoming_query = req.get("request").get("intent").get("slots").get("message").get("value")
            hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'
            # global OutMap
            OutMap = {}
            (input_sentence, OutMap) = hashMap_columns(str(incoming_query).lower(), hashColumn_csv, OutMap)
            print(input_sentence)
            print(OutMap)
            # print(query for query in queries)
            queries = parser.parse_sentence(input_sentence)
            queryString = ""
            table = ""
            for query in queries:
                table = query.get_from().get_table()
                columns = query.get_select().get_columns()
                conditions = query.get_where().get_conditions()
                queryString = queryString + str(query)
            print("table:")
            print(table)
            # print(list(columns))
            print(columns)
            print(columns[0])
            # print(columns[1])
            # xAxis = columns[0][0].split('.')[1]
            # yAxis = columns[1][0].split('.')[1]
            print(queryString)
            cur = conn.cursor()
            cur.execute(queryString)
            rows = cur.fetchall()
            cur.close()
            conn.close()

            # outText = ', '.join(str(x) for x in rows[0])
            # outText = ', '.join(str(element).split(".")[0] for row in rows for element in row)
            count = 0
            if len(conditions) != 0:
                whereColumn = []
                whereValue = []
                for i in range(0, len(conditions)):
                    print(conditions[i][1].get_column().rsplit('.', 1)[1].rstrip(')'))
                    print(conditions[i][1].get_value().strip("'"))
                    whereColumn.append(conditions[i][1].get_column().rsplit('.', 1)[1].rstrip(')'))

                    if " MAX" not in conditions[i][1].get_value() and " MIN" not in conditions[i][1].get_value():
                        whereValue.append(conditions[i][1].get_value().strip("'"))
                    else:
                        if " MAX" in conditions[i][1].get_value():
                            whereValue.append("max")
                        else:
                            whereValue.append("min")
            outText = "The "
            # if len(rows)==1:
            print("length of rows")
            print(len(rows))
            print(rows)

            if len(rows) == 1:
                for row in rows:
                    print(count)
                    isLast = len(row)
                    for element in row:
                        isLast = isLast - 1
                        value = str(element).split(".")[0]

                        if (columns[count][0] is not None):
                            # print(columns)
                            column = columns[count][0].split('.')[1]
                            print(column)
                        operation = columns[count][1]

                        if (operation is None):
                            print("The Operation is None")
                            column = OutMap.get(column)
                            whereValue1 = OutMap.get(whereValue[0]) if (OutMap.get(whereValue[0])) else whereValue[0]
                            whereColumn1 = OutMap.get(whereColumn[0]) if (OutMap.get(whereColumn[0])) else whereColumn[
                                0]
                            try:
                                print(whereValue[1])
                                print(whereColumn[1])
                                whereValue2 = OutMap.get(whereValue[1]) if (OutMap.get(whereValue[1])) else whereValue[
                                    1]
                                whereColumn2 = OutMap.get(whereColumn[1]) if (OutMap.get(whereColumn[1])) else \
                                whereColumn[1]
                                if 'whereColumn' in locals():
                                    # outText = str(column) + " " + value + " in the " + str(whereColumn1) + " " + str(
                                    #     whereValue1) + " has " + str(whereValue2) + " " + str(whereColumn2)
                                    outText = "The " + str(column) + " for " + str(whereColumn1) + " " + str(
                                        whereValue1) + " in " + str(whereColumn2) + " is " + value + "%"
                                else:
                                    outText = outText + str(column) + " is " + value

                            except IndexError:
                                if 'whereColumn' in locals():
                                    outText = str(column) + " " + value + " has " + str(whereValue1) + " " + str(
                                        whereColumn1)
                                else:
                                    outText = outText + str(column) + " is " + value

                        elif (operation is "COUNT"):
                            table = OutMap.get(table)
                            print("The Operation is " + str(operation))
                            if 'whereColumn' in locals():
                                outText = "There are " + value + " " + str(table) + " with " + str(
                                    whereValue[0]) + " " + str(whereColumn[0])
                            else:
                                outText = "There are " + value + " " + str(table)
                        else:
                            # operation = OutMap.get(str(operation).lower())
                            column = OutMap.get(column)
                            # whereValue = OutMap.get(whereValue)
                            print("The Operation is " + str(operation))
                            if 'whereColumn' in locals():
                                outText = "There are " + value + " " + str(column) + " in " + str(
                                    whereValue[0]) + " for " + str(whereValue[1]) + " " + str(whereColumn[1])
                            else:
                                if "what" in incoming_query:
                                    outText = "The " + OutMap.get(str(operation).lower()).lower() + " " + str(
                                        column) + " is " + value
                                elif "how" in incoming_query:
                                    outText = "There are " + value + " " + str(column)

                        if (isLast is not 0):
                            outText = outText + " and the "
                            count = count + 1

            else:
                print(whereColumn)
                print(whereValue)
                print(table)
                print(columns[1][0])
                column = columns[0][0].split('.')[1]
                column2 = columns[1][0].split('.')[1]
                sent_label = OutMap[column]
                sent_value = OutMap[column2]

                print(sent_label)
                outText = whereColumn[0] + " " + OutMap[whereValue[0]] + " has the following " + sent_label + ": "
                print(rows)
                print(columns)
                print(len(columns))

                no_of_rows = len(rows)
                counter = no_of_rows
                for row in rows:
                    counter = counter - 1
                    label = row[0]
                    value = row[1]
                    if counter != 0:
                        outText = outText + str(column) + " " + str(label) + " has " + str(column2) + " of " + str(
                            value) + ", "
                    else:
                        outText = outText + "whereas " + str(column) + " " + str(label) + " has " + str(
                            column2) + " of " + str(value)
                # outText = "The"
            print(outText)
            with open("response/alexa_response.json", 'r') as f:
                alexaResponse = json.load(f)

            alexaResponse["response"]["outputSpeech"]["text"] = outText
            return alexaResponse

        elif (req.get("request").get("intent").get("name") == "medicalvisualization"):

            url = urlparse("postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
            print (url.path[1:])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )

            print("Medical Visualization")
            # chartType = "line"
            incoming_query = req.get("request").get("intent").get("slots").get("message").get("value")
            print(incoming_query)
            chartType = req.get("request").get("intent").get("slots").get("charttypeslot").get("value")
            # if (chartType == "bar"):
            #     chartType = "bar"
            # else:
            #     chartType = "line"

            hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'
            OutMap = {}
            (input_sentence, OutMap) = hashMap_columns(str(incoming_query).lower(), hashColumn_csv, OutMap)
            print(OutMap)
            print(input_sentence)
            queries = parser.parse_sentence(input_sentence)
            # queries = parser.parse_sentence(incoming_query)
            # print(query for query in queries)
            queryString = ""
            table = ""
            for query in queries:
                table = query.get_from().get_table()
                columns = query.get_select().get_columns()
                conditions = query.get_where().get_conditions()
                queryString = queryString + str(query)

            # chartType = req.get("result").get("parameters").get("chart-type")
            # print(chartType)

            print(queryString)
            cur = conn.cursor()
            cur.execute(queryString)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            print(rows)
            print(list(columns))

            if len(columns) <= 2:
                xAxis = columns[0][0].split('.')[1]
                yAxis = columns[1][0].split('.')[1]
                xAxis = OutMap.get(xAxis) if OutMap.get(xAxis) else xAxis
                yAxis = OutMap.get(yAxis) if OutMap.get(yAxis) else yAxis
                print(xAxis)
                print(yAxis)
                print(chartType)
                df = pd.DataFrame(list(rows), columns=["label", "value"])
                df['value'] = df['value'].fillna(0)
                agg_df = df.groupby(['label'], as_index=False).agg({"value": "sum"})
                maxRecord = agg_df.ix[agg_df['value'].idxmax()].to_frame().T
                maxValue = agg_df['value'].max()
                print(maxRecord)
                print(maxValue)

                agg_df = agg_df.reset_index()
                minRecord = agg_df.ix[agg_df['value'].idxmin()].to_frame().T
                minValue = agg_df['value'].min()
                print(minRecord)
                print(minValue)

                agg_df['label'] = agg_df['label'].astype('str')
                agg_df['value'] = agg_df['value'].astype('str')

                agg_df.drop(columns=['index'], inplace=True)
                agg_df.reset_index(drop=True, inplace=True)
                print("agg_df:")
                print(agg_df)

                if chartType == 'geochart':
                    for id, cn in enumerate(agg_df['label']):
                        if cn == 'UK':
                            agg_df['label'][id] = 'GB'

                chartData = agg_df.to_json(orient='records')
                # chartData = [{"label": str(row[0]), "value": str(row[1])} for row in rows]
                print("agg_df:")
                print(agg_df)
                print("chartData:")
                print(chartData)
                # chartData = json.dumps(chartData)
                # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"xAxis", "yAxisName":"yAxis","source":[ { "label": "Mon", "value": "15123" }, { "label": "Tue", "value": "14233" }, { "label": "Wed", "value": "23507" }, { "label": "Thu", "value": "9110" }, { "label": "Fri", "value": "15529" }, { "label": "Sat", "value": "20803" }, { "label": "Sun", "value": "19202" } ]}]'
                final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

                print(final_json)

                socketio.emit('chartgoogledata', final_json)
                outText = "The " + xAxis + " " + str(
                    maxRecord['label'].values[0]) + " has maximum " + yAxis + " of " + str(
                    maxValue) + " while the " + xAxis + " " + str(
                    minRecord['label'].values[0]) + " has minimum " + yAxis + " of " + str(
                    minValue) + ". Refer to the screen for more details."
                # outText = "Refer to the screen for more details."
                print(outText)
                with open("response/alexa_response.json", 'r') as f:
                    alexaResponse = json.load(f)

                alexaResponse["response"]["outputSpeech"]["text"] = outText
                return alexaResponse


            else:
                xAxis = columns[0][0].split('.')[1]
                yAxis = columns[1][0].split('.')[1]
                zAxis = columns[2][0].split('.')[1]
                xAxis = OutMap.get(xAxis) if OutMap.get(xAxis) else xAxis
                yAxis = OutMap.get(yAxis) if OutMap.get(yAxis) else yAxis
                zAxis = OutMap.get(zAxis) if OutMap.get(zAxis) else zAxis

                print(xAxis)
                print(yAxis)
                print(zAxis)
                print(chartType)

                df = pd.DataFrame(list(rows), columns=["datatype", "country", "dq_score"])
                df['dq_score'] = df['dq_score'].fillna(0)
                # print(df)

                agg_df = df.groupby(['datatype', 'country'], as_index=False)['dq_score'].sum()
                print(agg_df)

                maxRecord = agg_df.ix[agg_df['dq_score'].idxmax()].to_frame().T
                agg_df = agg_df.reset_index()
                minRecord = agg_df.ix[agg_df['dq_score'].idxmin()].to_frame().T
                print(maxRecord)
                print(minRecord)
                agg_df['datatype'] = agg_df['datatype'].astype('str')
                agg_df['country'] = agg_df['country'].astype('str')
                agg_df.drop(columns=['index'], inplace=True)
                # agg_df.reset_index(drop=True, inplace=True)
                print("agg_df:")
                print(agg_df)

                pd.options.mode.chained_assignment = None

                for i in range(len(agg_df['datatype'])):
                    agg_df['datatype'][i] = agg_df['datatype'][i].replace(" ", "_")

                print(agg_df)

                unique_countries = set(agg_df['country'])
                unique_countries = list(unique_countries)

                unique_datatypes = set(agg_df['datatype'])
                unique_datatypes = list(unique_datatypes)

                df = agg_df
                df2 = pd.DataFrame(columns=['country', 'values'])
                df2['country'] = ['' for i in range(len(unique_countries))]

                for idx, cn in enumerate(unique_countries):
                    df2['country'][idx] = cn
                    df2['values'][idx] = {}

                for ind, val in enumerate(df2['values']):
                    for idx, dtyp in enumerate(unique_datatypes):
                        df2['values'][ind][dtyp] = 0

                for ind, cn in enumerate(df['country']):
                    for i, c in enumerate(df2['country']):
                        dat = df['datatype'][ind]
                        dqs = df['dq_score'][ind]
                        if cn == c:
                            df2['values'][i][dat] = dqs

                print(df2)

                agg_df = df2

                chartData = agg_df.to_json(orient='records')
                # chartData = [{"label": str(row[0]), "value": str(row[1])} for row in rows]
                print("agg_df:")
                print(agg_df)
                print("chartData:")
                print(chartData)
                # chartData = json.dumps(chartData)
                # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"xAxis", "yAxisName":"yAxis","source":[ { "label": "Mon", "value": "15123" }, { "label": "Tue", "value": "14233" }, { "label": "Wed", "value": "23507" }, { "label": "Thu", "value": "9110" }, { "label": "Fri", "value": "15529" }, { "label": "Sat", "value": "20803" }, { "label": "Sun", "value": "19202" } ]}]'
                final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

                print(final_json)

                socketio.emit('chartgoogledata', final_json)
                # outText = "The " + xAxis + " " + str(
                #     maxRecord['label'].values[0]) + " has maximum " + yAxis + " while the " + xAxis + " " + str(
                #     minRecord['label'].values[0]) + " has minimum " + yAxis + ". Refer to the screen for more details."
                outText = "Refer to the screen for more details."
                print(outText)
                with open("response/alexa_response.json", 'r') as f:
                    alexaResponse = json.load(f)

                alexaResponse["response"]["outputSpeech"]["text"] = outText
                return alexaResponse






if __name__ == '__main__':
    database = Database.Database()
    database.load("cognitiveSQL/database/HCM.sql")
    database.print_me()

    config = LangConfig.LangConfig()
    config.load("cognitiveSQL/lang/english.csv")

    parser = Parser.Parser(database, config)
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    port = int(os.getenv('PORT', 5001))

    print("Starting app on port %d" % port)

    #app.run(debug=True, port=port, host='0.0.0.0')
    socketio.run(app, debug=True, port=port, host='0.0.0.0')