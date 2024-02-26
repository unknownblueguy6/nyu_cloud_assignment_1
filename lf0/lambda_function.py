import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

client = boto3.client('lexv2-runtime')

def lambda_handler(event, context):
    print(event)
    
    # Specify your Lex V2 bot details
    bot_id = "D5ADX0KKMC"  
    bot_alias_id = "TSTALIASID"  
    locale_id = "en_US"
    
    session_id = None
    if len(event['messages']) > 1:
        session_id = event.get('sessionId', event['messages'][1]['unstructured']['text'])
    else:
        session_id = event.get('sessionId', 'testuser1')
        
    print(session_id)
    logger.debug('event.bot.name={}'.format(session_id))
    
    # if event[session_id] present in dynamo:
    #     call previous_Reco intent
        
    # else:
    user_message = event['messages'][0]['unstructured']['text']
    response = client.recognize_text(
        botId=bot_id,
        botAliasId=bot_alias_id,
        localeId=locale_id,
        sessionId=session_id,
        text=user_message
    )

    print(response)
    
    # Check if the Lex call was successful
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        # Construct a list of messages for all the content returned from Lex
        messages = []
        for msg in response['messages']:
            messages.append({
                "type": "unstructured",
                "unstructured": {
                    "id": str(session_id),  # Using session_id as a placeholder for the id
                    "text": msg['content'],  # The text content from Lex
                    "timestamp": "string"  # You may want to use the current time here
                }
            })
            
        # Return the list of messages back to the frontend
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'  # To allow cross-origin requests
            },
            "messages": messages
        }

    # If the Lex response is not successful, return a generic error message
    return {
        'statusCode': 500,
        'body': json.dumps('Error processing the Lex response')
    }
