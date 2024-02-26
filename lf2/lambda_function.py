import boto3
import json
import requests
import os
import random

# Initialize the SQS client
sqs = boto3.client('sqs')
ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def send_email(suggestion, restaurants):
    message_text = f"Hello, the following are my personal recommendations for {restaurants[0]['cuisine']} restaurants in {suggestion['Location']} at {suggestion['Time']} on {suggestion['Date']} for {suggestion['NumberOfPeople']} people:\n" + \
    f"1. {restaurants[0]['name']} Rating: {restaurants[0]['rating']} Address: {','.join(restaurants[0]['location']['display_address'])} Phone Number: {restaurants[0]['display_phone']}\n"+ \
    f"2. {restaurants[1]['name']} Rating: {restaurants[1]['rating']} Address: {','.join(restaurants[1]['location']['display_address'])} Phone Number: {restaurants[1]['display_phone']}\n"+ \
    f"3. {restaurants[2]['name']} Rating: {restaurants[2]['rating']} Address: {','.join(restaurants[2]['location']['display_address'])} Phone Number: {restaurants[2]['display_phone']}\n"
    
    subject_text = 'Dining Concierge Bot Suggestions!'
    
    return ses.send_email(
        Source='pb2846@nyu.edu',
        Destination={
            'ToAddresses':[suggestion['Email']]
        },
        Message={
            'Subject':{
                'Data':subject_text
            },
            'Body':{
                'Text':{
                    'Data': message_text
                }
            }
        }
    )


NUM_RESULTS = 3

def lambda_handler(event, context):
    queue_url = 'https://sqs.us-east-1.amazonaws.com/339712725968/DiningSuggestionsQueue'
    search_url = 'https://search-restaurants-dnzcdl2z7zpiumszpjavcalmte.aos.us-east-1.on.aws/restaurant/_search'
    
    restaurant_table = dynamodb.Table('yelp-restaurants')
    users_table = dynamodb.Table('users')
    
    # Receive a message from the SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MaxNumberOfMessages=1  # Adjust if you want to process more messages at once
    )
    
    messages = response.get('Messages', [])
    if messages:
        # Process the message (here, we simply print it)
        
        #{"Cuisine": "italian", "Email": "pb2846@nyu.edu", "Location": "Manhattan", "Time": "16:00", "NumberOfPeople": "5", "Date": "2024-02-26", "SessionID": "myu54h"}
        suggestion_info = json.loads(messages[0]['Body'])
        search_response = requests.get(search_url, json={"query":{"match_phrase":{"cuisine":suggestion_info["Cuisine"]}}}, auth=(os.environ.get('ES_MASTER_USERNAME'), os.environ.get('ES_MASTER_PASSWORD')))
        
        hits = (search_response.json())['hits']['hits']
        
        print(suggestion_info)
        # print(hits)
        
        restaurants = []
        selected_ind = []
        if len(hits) > 0:
            for i in range(NUM_RESULTS):
                    ind = random.randrange(len(hits))
                    while ind in selected_ind:
                        ind = random.randrange(len(hits))
                    selected_ind.append(ind)
                    db_response = restaurant_table.get_item(Key={
                        'id': hits[ind]['_source']['id']
                    })
                    
                    if 'Item' in db_response:
                        restaurants.append(db_response['Item'])
                        print(restaurants[-1])
                    
                    chosen_cuisine = restaurants[0]['cuisine']
                        
            
            users_table.put_item(
                Item={
                    'session_id': suggestion_info['SessionID'],
                    'chosen_cuisine': chosen_cuisine,
                    'recommendation_ids': [r['id'] for r in restaurants],
                    'email': suggestion_info['Email'],  # Added Email
                    'location': suggestion_info['Location'],  # Added Location
                    'time': suggestion_info['Time'],  # Added Time
                    'number_of_people': suggestion_info['NumberOfPeople'],  # Added NumberOfPeople
                    'date': suggestion_info['Date'],  # Added Date
                }
            )
        
            send_email(suggestion_info, restaurants)
        
        else:
            print("no results")
            
            
        # Delete the message from the queue after processing
        receipt_handle = messages[0]['ReceiptHandle']
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )

        return {
            'statusCode': 200,
            'body': json.dumps('Message processed from the queue and email sent.')
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps('No messages to process')
        }
