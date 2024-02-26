import boto3
import datetime
import dateutil.parser
import json
import logging
import math
import os
import time
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']

def close(session_attributes, fulfillment_state, message):
    return {
        "sessionState": {
            "sessionAttributes": session_attributes,
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": "DiningSuggestionsIntent",
                "state": fulfillment_state,
            }
        },
        "messages": [message] 
    }

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot
        }
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        "sessionState": {
            "sessionAttributes": session_attributes,
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": slot_to_elicit,
            },
            "intent": {
                "name": intent_name,
                "slots": slots,
                "state": "InProgress"  
            }
        },
        "messages": [message]
    }

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')

def delegate(session_attributes, slots):
    return {
        "sessionState": {
            "sessionAttributes": session_attributes,
            "dialogAction": {
                "type": "Delegate",
            },
            "intent": {
                "name": "DiningSuggestionsIntent",  
                "slots": slots,
                "state": "InProgress"
            }
        }
    }

def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)

def dispatch(intent_request):
    logger.debug(
        'dispatch userId={}, intentName={}'.format(intent_request['sessionId'], intent_request['sessionState']['intent']['name']))
    intent_name = intent_request['sessionState']['intent']['name']
    
    if intent_name == 'DiningSuggestionsIntent':
        return dining_suggestion_intent(intent_request)
    elif intent_name == 'PreviousRecommendationIntent':
        return previous_recommendation_intent(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')
    
def get_user_previous_search(session_id, users_table):
    try:
        response = users_table.get_item(Key={'session_id': session_id})
        if 'Item' in response:
            return response['Item']
        else:
            print("No previous search found for session_id:", session_id)
            return None
    except Exception as e:
        print("Error fetching user previous search from DynamoDB:", e)
        return None
        
def previous_recommendation_intent(intent_request):
    users_table = dynamodb.Table('users')
    
    session_id = intent_request['sessionId']
    user_data = get_user_previous_search(session_id, users_table)
    
    if user_data:
        print(user_data)
        
        email = user_data['email']
        location = user_data['location']
        cuisine = user_data['chosen_cuisine']
        date = user_data['date']
        time = user_data['time']
        number_of_people = user_data['number_of_people']
        recommendation_ids = user_data['recommendation_ids']
        
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName='DiningSuggestionsQueue')

        msg = {"Cuisine": cuisine, "Email": email, "Location": location, "Time": time, "NumberOfPeople": number_of_people, "Date": date, "SessionID":session_id}
        response = queue.send_message(
            MessageAttributes={
                'Cuisine': {
                    'DataType': 'String',
                    'StringValue': cuisine
                },
                'Email': {
                    'DataType': 'String',
                    'StringValue': email
                },
                'Location': {
                    'DataType': 'String',
                    'StringValue': location
                },
                'Time': {
                    'DataType': 'String',
                    'StringValue': time
                },
                'NumberOfPeople': {
                    'DataType': 'String',
                    'StringValue': number_of_people
                },
                'Date': {
                    'DataType': 'String',
                    'StringValue': date
                },
                'SessionID': {
                    'DataType': 'String',
                    'StringValue': session_id
                }
            },
            MessageBody=json.dumps(msg),
        )
    # logger.debug(f"final json: {intent_request}")
    return close(intent_request['sessionState']['sessionAttributes'],
             'Fulfilled',
             {'contentType': 'PlainText',
              'content': f'New dining suggestions have been sent to {email}.'
             })

def validate_dining_suggestion(location, cuisine, num_people, date, time, email):
    locs = ["manhattan"]
    if location is not None and location.lower() not in locs:
        return build_validation_result(False,
                                      'Location',
                                      'Location not supported. We only support Manhattan as of now.')

    cuisines = ['italian', 'chinese', 'indian', 'mexican', 'middle eastern']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                      'Cuisine',
                                      'Cuisine not available. Please try another cuisine')

    if num_people is not None:
        num_people = int(num_people)
        if num_people > 20 or num_people < 0:
            return build_validation_result(False, 'NumberOfPeople', 'Maximum 20 people allowed. Try again')
    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'Date',
                                            'I did not understand that, what date would you like to book?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'Date', 'Sorry Invalid Date, please enter a valid date')

    if time is not None:
        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(False, 'Time', 'Not a valid time')

        if hour < 6 or hour >= 23:
            return build_validation_result(False, 'Time', 'Our business hours are from 6 AM to 11 PM. Can you specify a time during this range?')

            
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if email is not None and not re.match(email_regex, email):
        return build_validation_result(False, 'Email', 'The email address format is invalid. Please provide a valid email.')
    
    return build_validation_result(True, None, None)

def dining_suggestion_intent(intent_request):
    print(f"intent_request: {intent_request}")
    location = get_slots(intent_request)["Location"]['value']['interpretedValue'] if get_slots(intent_request)["Location"] else None
    cuisine = get_slots(intent_request)["Cuisine"]['value']['interpretedValue'] if get_slots(intent_request)["Cuisine"] else None
    num_people = get_slots(intent_request)["NumberOfPeople"]['value']['interpretedValue'] if get_slots(intent_request)["NumberOfPeople"] else None
    date = get_slots(intent_request)["DiningDate"]['value']['interpretedValue'] if get_slots(intent_request)["DiningDate"] else None
    time = get_slots(intent_request)["DiningTime"]['value']['interpretedValue'] if get_slots(intent_request)["DiningTime"] else None
    email = get_slots(intent_request)["Email"]['value']['originalValue'] if get_slots(intent_request)["Email"] else None
    source = intent_request['invocationSource']
    sessionid_cookie = intent_request['sessionId']
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggestion(location, cuisine, num_people, date, time, email)
        
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionState']['sessionAttributes'],
                               intent_request['sessionState']['intent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        
        if intent_request['sessionState']['sessionAttributes'] is not None:
            output_session_attributes = intent_request['sessionState']['sessionAttributes']
        else:
            output_session_attributes = {}

        return delegate(output_session_attributes, get_slots(intent_request))
    
    if source  == "FulfillmentCodeHook":
        if cuisine is not None and email is not None and location is not None:
            sqs = boto3.resource('sqs')
            queue = sqs.get_queue_by_name(QueueName='DiningSuggestionsQueue')
            msg = {"Cuisine": cuisine, "Email": email, "Location": location, "Time": time, "NumberOfPeople": num_people, "Date": date, "SessionID":sessionid_cookie}
            response = queue.send_message(
                MessageAttributes={
                    'Cuisine': {
                        'DataType': 'String',
                        'StringValue': cuisine
                    },
                    'Email': {
                        'DataType': 'String',
                        'StringValue': email
                    },
                    'Location': {
                        'DataType': 'String',
                        'StringValue': location
                    },
                    'Time': {
                        'DataType': 'String',
                        'StringValue': time
                    },
                    'NumberOfPeople': {
                        'DataType': 'String',
                        'StringValue': num_people
                    },
                    'Date': {
                        'DataType': 'String',
                        'StringValue': date
                    },
                    'SessionID': {
                        'DataType': 'String',
                        'StringValue': sessionid_cookie
                    }
                },
                MessageBody=json.dumps(msg),
            )
        logger.debug(f"final json: {intent_request}")
        return close(intent_request['sessionState']['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thank you! You will recieve the suggestion shortly'})