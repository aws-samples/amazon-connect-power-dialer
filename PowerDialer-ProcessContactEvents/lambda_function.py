#Process ContactsEvents
import json
import base64
import boto3
import os
from powerdialer import get_token, sendSuccessToken, remove_contactId
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    if(event['detail'].get('eventType') =='DISCONNECTED'):
        contactId = str(event['detail']['contactId'])
        token = get_token(contactId,ACTIVE_DIALING)
        print ("ContactId:" + contactId)

        if(token!= None):
            print("Sending Token")
            print("Token:" + token)
            try:
                sendresult = sendSuccessToken(token,contactId)
            except Exception as e:
                    print (e)
            else:
                
                print(sendresult)
        else:
            print("No token")

    return
