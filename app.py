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

import json
import os
import math

import sys
sys.path.append('cognitiveSQL')

from flask import Flask
from flask import request
from flask import make_response
from flask import url_for, redirect
import psycopg2

import apiai
# Flask app should start in global layout
app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)
parser = ""

url = urlparse("postgres://caedtehsggslri:4679ba0abec57484a1d7ed261b74e80b08391993433c77c838c58415087a9c34@ec2-107-20-255-96.compute-1.amazonaws.com:5432/d5tmi1ihm5f6hv")
print (url.path[1:])
conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

# @app.route('/')
# def index():
#     return redirect(url_for('static_url', filename='index.html'))


@app.route('/speech')
def speech():
    return redirect(url_for('static', filename='index.html'))

# @app.route('/inventory')
# def inventory():
#     return redirect(url_for('static_url', filename='index.html'))

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
    if (req.get("result").get("action") == "medical.search"):
        print("Medical Search")
        incoming_query = req.get("result").get("resolvedQuery")
        hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'
        global OutMap
        OutMap={}
        (input_sentence, OutMap) = hashMap_columns(str(incoming_query).lower(), hashColumn_csv, OutMap)
        print(input_sentence)
        print(OutMap)
        #print(query for query in queries)
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
        #print(list(columns))
        print(columns)
        print(columns[0])
        #print(columns[1])
        # xAxis = columns[0][0].split('.')[1]
        # yAxis = columns[1][0].split('.')[1]
        print(queryString)
        cur = conn.cursor()
        cur.execute(queryString)
        rows = cur.fetchall()

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
                        whereColumn1 = OutMap.get(whereColumn[0]) if (OutMap.get(whereColumn[0])) else whereColumn[0]
                        try:
                            print(whereValue[1])
                            print(whereColumn[1])
                            whereValue2 = OutMap.get(whereValue[1]) if (OutMap.get(whereValue[1])) else whereValue[1]
                            whereColumn2 = OutMap.get(whereColumn[1]) if (OutMap.get(whereColumn[1])) else whereColumn[1]
                            if 'whereColumn' in locals():
                                # outText = str(column) + " " + value + " in the " + str(whereColumn1) + " " + str(
                                #     whereValue1) + " has " + str(whereValue2) + " " + str(whereColumn2)
                                outText = "The " + str(column) + " for " + str(whereColumn1) + " " + str(whereValue1)+ " in " + str(whereColumn2) + " is " + value + "%"
                            else:
                                outText = outText + str(column) + " is " + value

                        except IndexError:
                            if 'whereColumn' in locals():
                                outText = str(column) + " " + value + " has " + str(whereValue1) + " " + str(whereColumn1)
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
            sent_label=OutMap[column]
            sent_value=OutMap[column2]

            print(sent_label)
            outText=whereColumn[0]+ " " + OutMap[whereValue[0]] + " has the following " + sent_label + ":"
            print(rows)
            print(columns)
            print(len(columns))

            for row in rows:
                label=row[0]
                value=row[1]
                outText = outText + str(column) + " " + str(label) + " has " + str(column2)+ " " + str(value) + ", "

            #outText = "The"
        print(outText)

        return {
            "speech": outText,
            "displayText": outText,
            # "data": data,
            # "contextOut": [],
            "source": "Dhaval"
        }
    elif (req.get("result").get("action") == "medical.visualization"):
        print("Medical Visualization")
        #chartType = "line"
        incoming_query = req.get("result").get("resolvedQuery")
        print(incoming_query)
        chartType = req.get("result").get("parameters").get("chart-type")
        # if (chartType == "bar"):
        #     chartType = "bar"
        # else:
        #     chartType = "line"

        hashColumn_csv = 'cognitiveSQL/alias/synonyms.csv'
        OutMap={}
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
        print(rows)
        print(list(columns))
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
        agg_df = agg_df.reset_index()
        minRecord = agg_df.ix[agg_df['value'].idxmin()].to_frame().T
        agg_df['label'] = agg_df['label'].astype('str')
        agg_df['value'] = agg_df['value'].astype('str')

        agg_df.drop(columns=['index'], inplace=True)
        agg_df.reset_index(drop=True, inplace=True)

        chartData = agg_df.to_json(orient='records')
        # chartData = [{"label": str(row[0]), "value": str(row[1])} for row in rows]
        print("agg_df:")
        print(agg_df)
        print("chartData:")
        print(chartData)
        # chartData = json.dumps(chartData)
        #final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"xAxis", "yAxisName":"yAxis","source":[ { "label": "Mon", "value": "15123" }, { "label": "Tue", "value": "14233" }, { "label": "Wed", "value": "23507" }, { "label": "Thu", "value": "9110" }, { "label": "Fri", "value": "15529" }, { "label": "Sat", "value": "20803" }, { "label": "Sun", "value": "19202" } ]}]'
        final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

        # if chartType == "column2d":
        # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"barchart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'
        # elif chartType == "line":
        # final_json = '[ { "type":"' + chartType + '", "chartcontainer":"linechart", "caption":"A ' + chartType + ' chart showing ' + xAxis + ' vs ' + yAxis + '", "subCaption":"", "xAxisName":"' + xAxis + '", "yAxisName":"' + yAxis + '", "source":' + chartData + '}]'

        print(final_json)

        socketio.emit('chartgoogledata', final_json)
        outText = "The " + xAxis + " " + str(
            maxRecord['label'].values[0]) + " has maximum " + yAxis + " while the " + xAxis + " " + str(
            minRecord['label'].values[0]) + " has minimum " + yAxis + ". Refer to the screen for more details."
        # outText = "Refer to the screen for more details."
        print(outText)
        return {
            "speech": outText,
            "displayText": outText,
            # "data": data,
            # "contextOut": [],
            "source": "Dhaval"
        }




if __name__ == '__main__':

    # from os import sys, path
    # sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    # port = int(os.getenv('PORT', 5000))
    #
    # print("Starting app on port %d" % port)
    #
    # app.run(debug=True, port=port, host='0.0.0.0')
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