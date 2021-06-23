#Process AgentsEvents
import json
import base64
import boto3
import os
from powerdialer import get_token, sendSuccessToken, remove_contactId
from boto3.dynamodb.conditions import Key

ACTIVE_DIALING = os.environ['ACTIVE_DIALING']
DIALER_CONFIG=os.environ['CONFIG_TABLE']


def lambda_handler(event, context):
    for record in event['Records']:
        payload=base64.b64decode(record["kinesis"]["data"])
        contactRecord = json.loads(payload)
        print("Full: " + str(payload))
        
        try:
            eventType = str(contactRecord['EventType'])
        except KeyError:
            eventType= "CTR_EVENT"
            
        if(eventType== "CTR_EVENT"and 'DisconnectReason' in contactRecord and contactRecord['DisconnectReason']=="CUSTOMER_DISCONNECT"):
            print ("Customer Disconnection")
            contactId = str(contactRecord['ContactId'])
            token = get_token(contactId,ACTIVE_DIALING)

            if(token!= None):
                print("Enviando Token")
                print ("ContactId:" + contactId)
                print("Token:" + token)
                try:
                    sendresult = sendSuccessToken(token,contactId)
                    remove_contactId(contactId,ACTIVE_DIALING)
                except Exception as e:
                        print (e)
                else:
                    
                    print(sendresult)

        if(eventType== "STATE_CHANGE"):
            print ("Agent Event")
            if (contactRecord['PreviousAgentSnapshot'] is not None):
                
                for contact in contactRecord['PreviousAgentSnapshot']['Contacts']:
                    prevContactState=contact['State']
                    prevContactId=contact['ContactId']
                    if(prevContactState == "ENDED" or prevContactState =="ERROR"):
                        print(str(prevContactState))
                        print("PrevContactId:" + str(prevContactId))
                        token = get_token(prevContactId,ACTIVE_DIALING)
                        if(token!= None):
                            print("Enviando Token")
                            print ("ContactId:" + prevContactId)
                            print("Token:" + token)
                            try:
                                sendresult = sendSuccessToken(token,prevContactId)
                                remove_contactId(prevContactId,ACTIVE_DIALING)
                            except Exception as e:
                                    print (e)
                            else:
                                print(sendresult)

    return