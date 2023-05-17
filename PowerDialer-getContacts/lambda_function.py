##getContacts Function
import json
import boto3
import os
from powerdialer import get_config, get_callee, update_dial_list, update_config, delete_contact
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print(event)
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    SQS_URL = os.environ['SQS_URL']
    availAgents = int(event['availAgents'])
    contacts = []
    endOfList = "False"
    if(availAgents>10):
        ## Logic for implementing over 10 concurrent calls. [WIP]
        messages = []
        for i in range(round(availAgents/10)):
            msgblock = get_contact(availAgents,SQS_URL)
            messages.append(msgblock)
    else:
        messages = get_contact(availAgents,SQS_URL)

    if messages is not None:
        for message in messages:
            print("Received: " + message['custID'])
            contacts.append(dict([('custID',message['custID']),('phone',message['phone']),('attributes',message['attributes'])]))
            delete_contact(message['ReceiptHandle'],SQS_URL)
    else:
        print("No additional items")
        endOfList = "True"
    
    contactResponse = dict([("EndOfList",endOfList),("contacts",contacts)])

    print(contactResponse)
    return contactResponse


def get_contact(quantity,sqs_url):
    sqs = boto3.client('sqs')
    try:
        response = sqs.receive_message(
            QueueUrl=sqs_url,
            MaxNumberOfMessages=quantity,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=10,
            WaitTimeSeconds=3
            )
    except:
        return None
    else:
        messages=[]
        if 'Messages' in response:
            for message in response['Messages']:
                msg = {
                    'ReceiptHandle':message['ReceiptHandle'],
                    'phone': message['MessageAttributes']['phone']['StringValue'], #message['Body'],
                    'custID': message['MessageAttributes']['custID']['StringValue'],
                    'attributes': json.loads(message['MessageAttributes']['attributes']['StringValue'])
                    }
                messages.append(msg)
            return messages
        else:
            return None


'''
##DDB Based Method
    DIALER_LIST_TABLE = get_config('table-dialerlist', DIALER_DEPLOYMENT)
    responseIndex = 0
    totalRecords = int(event['params']['totalRecords'])
    print("Total Records: " + str(totalRecords))
    index = int(get_config('dialIndex',DIALER_DEPLOYMENT))
    print("dialIndex: " + str(index))


    #Find the next phone in contact that has not been called.
    while(index<= totalRecords and responseIndex < availAgents):
        print("responseIndex: " + str(responseIndex))
        callee = get_callee(index, DIALER_LIST_TABLE)
        if(callee!=None and callee['callAttempted']==False):
            
            update_dial_list(index, 'callAttempted',True, DIALER_LIST_TABLE)
            print('Fetched: ')
            print('CustID: ' + callee['custID']+':'+callee['phone'])
            responseIndex+= 1
            contacts.append(dict([('custID',callee['custID']),('index', index),('phone',callee['phone']),('attributes',callee['attributes'])]))
            endOfList = "False"
            #return contactResponse
        else:
            index += 1
            print('No more contacts available for callee, increasing index:')
            print("dialIndex: " + str(index))
            if(index<=totalRecords):
                update_config('dialIndex', index, DIALER_DEPLOYMENT)
                
            else:
                print("No more callees")
                endOfList = "True"
'''