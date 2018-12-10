from flask import Flask,request, json
from flask import render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base
import recastai
import os
import requests
import pdb
import datetime
import time
from urllib.request import Request, urlopen
import dateutil.parser
from datetime import datetime

app = Flask(__name__)
app.config['DEBUG'] = True

#


# DB
Base = automap_base()
engine = create_engine('postgresql+psycopg2://root:rootroot@testdbinstance.cjgud0fxglke.us-east-1.rds.amazonaws.com:5432/insurance_info')
Base.prepare(engine, reflect=True)
Insurance = Base.classes.insurances
session = Session(engine)


RECAST_REQUEST_TOKEN = os.environ.get("API_REQUEST_TOKEN", default=None)
RECAST_DEVELOPER_TOKEN = os.environ.get("API_DEVELOPER_TOKEN", default=None)


@app.route('/')
def hello():
    insurances = session.query(Insurance).limit(10).all()
    return render_template('index.html', insurances=insurances)


@app.route('/api/v1/get_insurance_data', methods=['POST'])
def get_insurance_data():
    sampledata = {'nlp': {'uuid': 'cf771ba7-bc07-4520-8c1f-86f29c185d19', 'intents': [{'slug': 'insurancedetails', 'confidence': 0.99, 'description': None}], 'entities': {'policynumber': [{'value': '3123123', 'raw': '3123123', 'confidence': 0.87}]}, 'language': 'en', 'processing_language': 'en', 'version': '2.12.0-20a34c24', 'timestamp': '2018-11-29T06:12:23.139483+00:00', 'status': 200, 'source': '3123123', 'act': 'assert', 'type': None, 'sentiment': 'neutral'}, 'action_id': 'ed62dc85-d66f-4121-ac56-4034f95e1729', 'conversation': {'id': 'test-1543471909240', 'conversation_id': 'test-1543471909240', 'warning': 'The conversation_id field will be depreciated on January 1st 2018! Switch to using the id field instead', 'language': 'en', 'memory': {'policyNumber': {'value': '3123123', 'raw': '3123123', 'confidence': 0.87}}, 'skill_stack': ['askforinsurancenumber'], 'skill': 'askforinsurancenumber', 'skill_occurences': 2, 'participant_data': {}}}
    recast_response = json.loads(request.get_data())
    policy_number = recast_response['nlp']['entities']['policy_number'][0]['value']
    conversation_id = recast_response['conversation']['id']
    insurance_data = session.query(Insurance).filter_by(policy_number=policy_number)
    if insurance_data.count() == 0:
        response_message_obj = [{
            "type": "text",
            "content": "The policy you entered wasn't found. Please enter a valid policy number."
        }]
        data_to_store_in_memory = {
            "memory": {}
        }
    else:
        insurance_data = insurance_data.first()
        response_message_obj = [
            {
                "type": "text",
                "content":f"Policy with number {insurance_data.policy_number} found! Here are the details"
            },{
                "type": "card",
                "content": {
                    "title": "",
                    "subtitle": f"Account Name : {insurance_data.account_name} \n Premium : {insurance_data.premium}",
                    "imageUrl": "https://media.licdn.com/dms/image/C4E0BAQEqJ7-YxlwqSA/company-logo_200_200/0?e=2159024400&v=beta&t=7uwWiOsPAiYiv94Nr3tVZRfqeRVTXfObj2B1tPbAfL0",
                    "buttons": []
                }
            },{
                "type": "text",
                "content":"What else would you like to know? You can search for either of expiration date, policy status, address, phone number and policy type."
            }
        ]
        data_to_store_in_memory = {
            "memory" : {
                "policy_number": insurance_data.policy_number,
                "account_name": insurance_data.account_name,
                "premium": insurance_data.premium,
                "expiration_date": insurance_data.expiration_date.strftime('%d-%m-%Y'),
                "policy_status": insurance_data.status,
                "user_insurance_type":insurance_data.insurance_type,
                "user_insurance_address":insurance_data.address,
                "user_phone_number":insurance_data.phone_number,
                "plan":insurance_data.plan
            }
        }

    placeholder = [{
        "type": "text",
        "content": "Give me a minute, I'm searching for your policy"
    }]

    message_sent_response = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                                          headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                                          json={"messages": placeholder})
    time.sleep(20)
    store = requests.put(f'https://api.recast.ai/build/v1/users/kratiknayak/bots/insurance/versions/v1/builder/conversation_states/{conversation_id}',
                         headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                         json= data_to_store_in_memory)
    message_sent_response = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                                          headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                                          json={"messages": response_message_obj})
    return "OK"


@app.route('/api/v1/get_individual_details', methods=['POST'])
def get_policy_individual_details():
    recast_response = json.loads(request.get_data())
    entities = list(recast_response['nlp']['entities'].keys())
    all_entities = ['policy_number','premium','account_name','expiration_date','policy_status',"user_insurance_type","user_insurance_address","user_phone_number","plan"]
    memory = recast_response['conversation']['memory']
    conversation_id = recast_response['conversation']['id']
    entity_mapping = {"policy_number": "Policy Number",
                      "account_name": "Account Name",
                      "premium": "Premium",
                      "expiration_date": "Expiration Date",
                      "policy_status": "Policy Status",
                      "user_insurance_type": "Insurance Type",
                      "user_insurance_address": "Address",
                      "user_phone_number": "Phone Number",
                      "plan": "Plan"}
    response_message_obj = [{
        "type": "text",
        "content": "Here's what I found."
    }]
    resp = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                         headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                         json={"messages": response_message_obj})
    for entity in entities[:]:
        if entity not in all_entities:
            entities.remove(entity)

    for entity in entities:
        response_message_obj = [{
            "type": "text",
            "content": f"Your {entity_mapping[entity]}  is {memory[entity]}"
        }]
        resp = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                             headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                             json={"messages": response_message_obj})
    return "OK"


@app.route('/api/v1/select_insurance', methods=['POST'])
def buy_assistance():
    recast_response = json.loads(request.get_data())
    conversation_id = recast_response['conversation']['id']
    button_types = [{
        "type": "buttons",
        "content": {
            "title": "Please select from the options below",
            "buttons": [
                {
                    "title": "life",
                    "type": "postback",
                    "value": "life"
                },
                {
                    "title": "medical",
                    "type": "postback",
                    "value": "medical"
                },
                {
                    "title": "dental",
                    "type": "postback",
                    "value": "dental"
                }
            ]
        }
    }]
    resp = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                         headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                         json={"messages": button_types})
    return "Ok"


@app.route('/api/v1/show_policies', methods=['POST'])
def show_policies():
    recast_response = json.loads(request.get_data())
    print("==========================")
    print(recast_response['conversation']['memory'])
    print("==========================")
    conversation_id = recast_response['conversation']['id']
    memory = recast_response['conversation']['memory']
    number_of_family_members = None
    age = memory["age"]["raw"]
    print("============AGE============")
    print(age)
    print("===========AGE=============")
    str_term = recast_response["nlp"]["entities"]["term"][0]["raw"]
    if "family_members" in memory.keys():
        number_of_family_members = memory["family_members"]["raw"]
    if str_term == "5-years":
        term = 5
    elif str_term == "10-years":
        term = 10
    elif str_term == "15-years":
        term = 15
    response_message_obj = [{
        "type": "text",
        "content": "Here are some plans I found that you might like."
    }]
    insurance_data = session.query(Insurance).filter_by(age=age).limit(3).all()

    response_message_obj.append(create_carousel(insurance_data, term,number_of_family_members))

    if number_of_family_members is not None:
        value = f"https://protected-beyond-91709.herokuapp.com/api/v1/search?age={age}&term={term}&family_members={number_of_family_members}"
    else:
        value = f"https://protected-beyond-91709.herokuapp.com/api/v1/search?age={age}&term={term}"
    see_more = [{
        "type": "buttons",
        "content": {
            "title": "To see more like this",
            "buttons": [
                {
                    "title": "Click here",
                    "type": "web_url",
                    "value": value
                }
            ]
        }
    }]

    resp = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                         headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                         json={"messages": response_message_obj})
    resp = requests.post(f'https://api.recast.ai/connect/v1/conversations/{conversation_id}/messages',
                         headers={'Authorization': f'Token {RECAST_DEVELOPER_TOKEN}'},
                         json={"messages": see_more})
    print(resp.text)
    return "Okay"


def create_carousel(insurance_data,term,number_of_family_members):
    plans = []

    for i, insurance in enumerate(insurance_data, start=1):

        if number_of_family_members is not None:
            print(number_of_family_members, term, insurance.premium)
            sum_assured = int(insurance.premium) * int(term) * int(number_of_family_members)
            premium = insurance.premium * int(number_of_family_members)
        else:
            sum_assured = int(insurance.premium) * int(term)
            premium = insurance.premium
        plan = {
            "title": f"Plan type {insurance.plan}",
            "subtitle": f"Premium: ${premium}/mo, Sum assured: ${float(sum_assured)}",
            "imageUrl": "https://s3.amazonaws.com/images.productionhub.com/profiles/logos/325796_a5mdmymdaw.jpg",
            "buttons": []
        }
        plans.append(plan)
    list_of_plans = {
        "type": "carousel",
        "content": plans
    }
    return list_of_plans

@app.route('/api/v1/search', methods=['GET'])
def search_insurance():
    filter_params = request.args.to_dict()
    total_months = int(filter_params["term"])*12 if filter_params.get('term') else 12
    family_count = int(filter_params["family_members"]) if filter_params.get('family_members') else 1
    similar_insurances = session.query(Insurance).filter_by(age=filter_params["age"]).all()
    return render_template('search.html', insurances=similar_insurances, total_premium_multiplier=total_months*family_count)

if __name__ == '__main__':
    app.run()
