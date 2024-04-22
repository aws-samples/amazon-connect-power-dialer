##getContacts Function
import json
import boto3
import os
from powerdialer import delete_contact
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
            WaitTimeSeconds=5
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