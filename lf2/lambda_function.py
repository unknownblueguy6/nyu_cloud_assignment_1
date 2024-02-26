import boto3
import json
import requests
import os

# Initialize the SQS client
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    queue_url = 'https://sqs.us-east-1.amazonaws.com/339712725968/DiningSuggestionsQueue'
    search_url = 'https://search-restaurants-dnzcdl2z7zpiumszpjavcalmte.aos.us-east-1.on.aws/restaurants/_search'

    # Receive a message from the SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MaxNumberOfMessages=1  # Adjust if you want to process more messages at once
    )

    messages = response.get('Messages', [])
    if messages:
        # Process the message (here, we simply print it)
        suggestion_info = messages[0]['Body']
        
        search_response = requests.get(search_url, json={"query":{"match":{"cuisine":suggestion_info["Cuisine"]}}}, auth=(os.environ.get('ES_MASTER_USERNAME'), os.environ.get('ES_MASTER_PASSWORD')))
        print(search_response)
        # Delete the message from the queue after processing
        receipt_handle = messages[0]['ReceiptHandle']
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )

        return {
            'statusCode': 200,
            'body': json.dumps('Message processed from the queue')
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps('No messages to process')
        }
