#Process ContactsEvents
import json
import base64
import boto3
import os
from powerdialer import get_token, sendSuccessToken, remove_contactId
from boto3.dynamodb.conditions import Key

ACTIVE_DIALING = os.environ['ACTIVE_DIALING']


def lambda_handler(event, context):
    print(event)
    if(event['detail'].get('eventType') =='DISCONNECTED'):
        contactId = str(event['detail']['contactId'])
        token = get_token(contactId,ACTIVE_DIALING)
        print ("ContactId:" + contactId)

        if(token!= None):
            print("Sending Token")
            print("Token:" + token)
            try:
                sendresult = sendSuccessToken(token,contactId)
                #remove_contactId(contactId,ACTIVE_DIALING)
            except Exception as e:
                    print (e)
            else:
                
                print(sendresult)
        else:
            print("No token")

    return