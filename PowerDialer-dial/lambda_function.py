##dialer
import json
import boto3
import os
from datetime import datetime
from powerdialer import place_call, updateActiveDialing, save_results, get_token
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    print(event)
    
    ACTIVE_DIALING_TABLE = os.environ['ACTIVE_DIALING_TABLE']
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']
    
    contactFlow = event['params']['contactflow']
    connectID = event['params']['connectid']
    queue = event['params']['queue']
    task_token = event['TaskToken']
    phone = event['contacts']['phone']
    attributes = event['contacts']['attributes']
    #attributes['index'] = str(event['contacts']['index'])
    
    response = place_call(phone, contactFlow, connectID, queue,attributes)
    
    if(response):
        print("Valid response - Updating TOKEN")
        contactId = response['ContactId']
        
        token = get_token(contactId,ACTIVE_DIALING_TABLE)
        if(token!= None):
            print("Existing previous call attempt")
            send_task_success(token)
        else:
            print("Completed new call")
            validNumber= True
            updateActiveDialing(contactId, task_token, phone,ACTIVE_DIALING_TABLE)
            results = {'phone':phone,'validNumber':True,'contactId':contactId}
    else:
        print("Invalid response - Clearing TASK")
        validNumber=False
        contactId = "NoContact"
        send_task_success(task_token)
        results = {'phone':phone,'validNumber':False,'contactId':contactId}

    save_results(results,DIALER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)
    return {'validNumber':validNumber, 'contactId': contactId }

def send_task_success(task_token):
    sfn = boto3.client('stepfunctions')
    response = sfn.send_task_success(
        taskToken=task_token,
         output='{"Payload": {"callAttempt":"callAttemptFailed", "contactId":"NoContact"},"validNumber":"False"}'
    )