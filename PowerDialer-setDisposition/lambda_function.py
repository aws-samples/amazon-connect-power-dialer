##setDisposition Function
import json
import boto3
import os
from powerdialer import update_dial_list, save_results

connect=boto3.client('connect')
DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
RESULTS_FIREHOSE_NAME = os.environ['RESULTS_FIREHOSE_NAME']

def lambda_handler(event, context):    
    print(event)
    contactId = event['Details']['ContactData']['Attributes'].get('contactId',False)
    phone=event['Details']['ContactData'].get('CustomerEndpoint',False)
    
    results = {'CampaignStep':'CallCompleted','phone':phone,'contactId':contactId}

    if('Attributes' in event['Details']['ContactData'] and len(event['Details']['ContactData']['Attributes'])>0):
        for attkey in event['Details']['ContactData']['Attributes'].keys():
            results.update({attkey:event['Details']['ContactData']['Attributes'][attkey]})

    save_results(results,DIALER_DEPLOYMENT,RESULTS_FIREHOSE_NAME)

    return {
        'Saved': True
        } 