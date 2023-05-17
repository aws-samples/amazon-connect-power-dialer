##setDisposition Function
import json
import boto3
import os
from powerdialer import update_dial_list, save_results

connect=boto3.client('connect')

def lambda_handler(event, context):
    DIALING_LIST = os.environ['DIALING_LIST']
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']
    
    print(event)
    contactId = event['Details']['ContactData']['Attributes'].get('contactId',False)
    
    instanceArn= event['Details']['ContactData']['InstanceARN']
    dispositionCode= event['Details']['ContactData']['Attributes'].get('dispositionCode',False)
    #dialIndex= event['Details']['ContactData']['Attributes'].get('index',False)
    phone=event['Details']['ContactData']['Attributes'].get('phone',False)
    
    instanceId=instanceArn.split("/")[-1]
    results = {'phone':phone,'validNumber':True,'contactId':contactId}
    #update_dial_list(int(dialIndex), 'disposition', dispositionCode, DIALING_LIST)
    save_results(results,DIALER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)
    
    if(contactId and dispositionCode):
        response = connect.update_contact_attributes(
        InitialContactId=contactId,
        InstanceId=instanceId,
        Attributes={
            'disposition-code': dispositionCode
        }
        )
        return {
        'Tagged': True
        }
    return {
        'Tagged': False
        } 