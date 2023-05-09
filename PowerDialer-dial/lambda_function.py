##dialer
import json
import boto3
import os
from datetime import datetime
from powerdialer import place_call, updateActiveDialing
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    print(str(event))
    
    ACTIVE_DIALING_TABLE = os.environ['ACTIVE_DIALING_TABLE']
    
    contactFlow = event['params']['contactflow']
    connectID = event['params']['connectid']
    queue = event['params']['queue']
    TASK_TOKEN = event['TaskToken']
    phone = event['contacts']['phone']
    attributes = event['contacts']['attributes']
    attributes['index'] = str(event['contacts']['index'])
    
    response = place_call(phone, contactFlow, connectID, queue,attributes)
    
    if(response):
        print("Valid response - Updating TOKEN")
        contactId = response['ContactId']
        validNumber= True
        updateActiveDialing(contactId, TASK_TOKEN, phone,ACTIVE_DIALING_TABLE)
    else:
        print("Invalid response - Clearing TASK")
        validNumber=False
        contactId = "NoContact"
        sfn = boto3.client('stepfunctions')
        response = sfn.send_task_success(
            taskToken=TASK_TOKEN,
             output='{"Payload": {"callAttempt":"callAttemptFailed", "contactId":"NoContact"},"validNumber":"False"}'
        )


    return {'validNumber':validNumber, 'contactId': contactId }