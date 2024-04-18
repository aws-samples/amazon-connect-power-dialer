##dialer
import json
import boto3
import os
from datetime import datetime
from powerdialer import place_call, updateActiveDialing, save_results
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    print(str(event))
    
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']
    
    contactFlow = event['params']['contactflow']
    connectID = event['params']['connectid']
    queue = event['params']['queue']
    TASK_TOKEN = event['TaskToken']
    phone = event['contacts']['phone']
    attributes = event['contacts']['attributes']
    
    response = place_call(phone, contactFlow, connectID, queue,attributes)
    
    if(response):
        print("Valid response - Updating TOKEN")
        contactId = response['ContactId']
        validNumber= True
        results = {'phone':phone,'validNumber':True,'contactId':contactId}
    else:
        print("Invalid response - Clearing TASK")
        validNumber=False
        contactId = "NoContact"
        sfn = boto3.client('stepfunctions')
        response = sfn.send_task_success(
            taskToken=TASK_TOKEN,
             output='{"Payload": {"callAttempt":"callAttemptFailed", "contactId":"NoContact"},"validNumber":"False"}'
        )
        results = {'phone':phone,'validNumber':False,'contactId':contactId}

    save_results(results,DIALER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)
    return {'validNumber':validNumber, 'contactId': contactId }

