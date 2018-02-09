#!/usr/bin/env python

#test

from __future__ import print_function

import datetime
from future.standard_library import install_aliases

install_aliases()

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
parser = ""


# @app.route('/')
# def index():
#     return redirect(url_for('static_url', filename='index.html'))

def select_inquiry_response(prod_name, columnName):
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
        sql = "select " + columnName + " from public.inquiry_response where product_name = '%s' limit %s" %(prod_name,1)
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
    return redirect(url_for('static', filename='index.html'))

# @app.route('/inventory')
# def inventory():
#     return redirect(url_for('static_url', filename='index.html'))

@app.route('/medicalAffair', methods=['POST'])
def medicalAffair():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest    (req)

    res = json.dumps(res, indent=4)
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    print(req.get("result").get("action"))
    actionIncompleteStatus = req.get("result").get("actionIncomplete")
    print(actionIncompleteStatus)
    fac_unfac = ""
    master_prod=""
    response = ""
    status = False
    if actionIncompleteStatus:
        print("Skipping")
    else:
        print("Accepted")
        if ((req.get("result").get("action") is not None) or (req.get("result").get("parameters").get("ProductName") is not None) or (req.get("result").get("parameters").get("UserRegion") is not None) or (req.get("result").get("UserAge").get("amount") is not None) or (req.get("result").get("UserAge").get("unit") is not None)):
            if (req.get("result").get("action") == "ProdAppearance"):
                print("ProdApperance")
                Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),"Apperance")
                if Prod_Response != None:
                    status = True;
                    fac_unfac = 'Facilitated'
                    master_prod = 'Product Appearance'
                    response = Prod_Response[0]
                else:
                    status = False;
                    fac_unfac = 'Unfacilitated'
            elif (req.get("result").get("action") == "ProdAvailability"):
                print("ProdAvailability")
                Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),"Availability")
                if Prod_Response != None:
                    status = True;
                    fac_unfac = 'Facilitated'
                    master_prod = 'Product Availability'
                    response = Prod_Response[0]
                else:
                    status = False;
                    fac_unfac = 'Unfacilitated'
            elif (req.get("result").get("action") == "ProdGenericAvailability"):
                print("ProdGenericAvailable")
                Prod_Response = select_inquiry_response(req.get("result").get("parameters").get("ProductName"),"Generic_Availables")
                if Prod_Response != None:
                    status = True;
                    fac_unfac = 'Facilitated'
                    master_prod = 'Product Generic Availability'
                    response = Prod_Response[0]
                else:
                    status = False;
                    fac_unfac = 'Unfacilitated'
                #Default else
            else:
                status =False;

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


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    address = parameters.get("address")
    if address is None:
        return None
    city = address.get("city")
    # city = parameters.get("city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"

def makeSymptomsQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    symptoms = parameters.get("symptoms")
    #print(json.dumps(parameters))
    #print(json.dumps(symptoms))
    if symptoms is None:
        return None
    list = ",".join(symptoms)
    print (list)
    return "symptoms=[" + list + "]"

def makeDoctorQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    symptoms = parameters.get("symptoms2")
    print(json.dumps(symptoms))
    if symptoms is None:
        return None
    print(json.dumps(city))
    if city is None:
        return urlencode({'query': json.dumps(symptoms)})
    else:
        baseurl = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyCQiBWiGy-aaNrthZCShG8sOs3G_ynJkEI&"
        q = urlencode({'address': city})
        yql_url = baseurl + q
        print(yql_url)
        result = urlopen(yql_url).read()
        print(json.dumps(result))
        data = json.loads(result)
        response2 = data.get('results')
        if response2 is None:
            return None
        print(json.dumps(response2))
        latitude = response2[0]['geometry']['location']['lat']
        longitude = response2[0]['geometry']['location']['lng']
        if (latitude is None) or (longitude is None):
            return None
        print(json.dumps(latitude))
        print(json.dumps(longitude))
        return urlencode({'query': json.dumps(symptoms), 'location': latitude + "," + longitude})

def makeWebhookWeatherResult(data):
    query = data.get('query')
    if query is None:
        return {}
    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
             "the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "virtual-patient-assistant"
    }

def makeWebhookTemperatureResult(data):
    print(json.dumps(data))
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " \
             ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "virtual-patient-assistant"
    }

def makeWebhookDiagnosisResult(data):
    result = data[0]
    if result is None:
        return {}

    issue = result['Issue']
    if issue is None:
        return {}
    print(issue)
    name = result['Issue']['Name']
    id = result['Issue']['ID']
    if name is None:
        return {}

    diagnosis = result['Issue']['IcdName']
    if diagnosis is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "You might be experiencing " + name + ". These are signs of " + diagnosis

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        "contextOut": [{"name":"identifydisease-followup", "lifespan":5, "parameters":{"issue":id}}],
        "source": "virtual-patient-assistant"
    }

def makeWebhookInfoResult(data):
    description = data['Description']
    if description is None:
        return {}
    #print(description)
    #name = result['Issue']['Name']
    #id = result['Issue']['ID']
    #if name is None:
    # return {}

    #diagnosis = result['Issue']['IcdName']
    #if diagnosis is None:
    #    return {}

    # print(json.dumps(item, indent=4))

    #speech = "You might be experiencing " + name + ". These are signs of " + diagnosis

    #print("Response:")
    #print(description)

    return {
        "speech": description,
        "displayText": description,
        # "data": data,
        #"contextOut": [{"name":"identifydisease-followup", "lifespan":5, "parameters":{"issue":id}}],
        "source": "virtual-patient-assistant"
    }

def makeWebhookDiseaseResult(data):
    description = data['PossibleSymptoms']
    if description is None:
        return {}
    #print(description)
    #name = result['Issue']['Name']
    #id = result['Issue']['ID']
    #if name is None:
    # return {}

    #diagnosis = result['Issue']['IcdName']
    #if diagnosis is None:
    #    return {}

    # print(json.dumps(item, indent=4))

    speech = "Probable symptoms are " + description

    #print("Response:")
    #print(description)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        #"contextOut": [{"name":"identifydisease-followup", "lifespan":5, "parameters":{"issue":id}}],
        "source": "virtual-patient-assistant"
    }


def makeWebhookDoctorResult(data):
    result = data.get('data')
    if result is None:
        return {}
    #print(json.dumps(result, indent=4))

    docList = result[0]
    if docList is None:
        return {}

    #print(json.dumps(docList, indent=4))
    practices = docList['practices'][0]
    if practices is None:
        return {}
    #print(json.dumps(practices, indent=4))

    name = practices['name']
  #  print(json.dumps(name, indent=4))

    visit_address = practices['visit_address']['city']
   # print(json.dumps(visit_address, indent=4))

    phones = practices['phones'][0]['number']

   # print(json.dumps(phones, indent=4))

    speech = "Please visit Dr. " + name + ". The clinic is located in " + visit_address + ". For further details, contact him at " + phones + ". Do you want to schedule an appointment?"

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        "contextOut": [{"name":"identifydoctor-followup", "lifespan":5, "parameters":{"doctor":name}}],
        "source": "virtual-patient-assistant"
    }

if __name__ == '__main__':

    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=True, port=port, host='0.0.0.0')
