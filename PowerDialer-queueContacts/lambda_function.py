##Add Pinpoint contacts to queue
import json
import os
import boto3
from powerdialer import queue_contact,update_config,get_config

SQS_URL = os.environ['SQS_URL']
DIALER_DEPLOYMENT= os.environ['DIALER_DEPLOYMENT']
SFN_ARN = os.environ['SFN_ARN']

def lambda_handler(event, context):
    print(event)
    endpoints =event['Endpoints']
    index=0
    errors=0
    ApplicationId= event['ApplicationId']
    CampaignId= event['CampaignId']
    for epkey in endpoints.keys():
        data = get_endpoint_data(endpoints[epkey])
        if(data):
            try:
                queue_contact(data['custID'],data['phone'],data['attributes'],SQS_URL)
            except:
                print("Error while queueing:" + str(data['phone']))
                errors+=1
            else:
                index+=1
    
    if(index):
        print("Contacts added to queue, validating dialer status.")
        dialerStatus = get_config('activeDialer', DIALER_DEPLOYMENT)
        print(dialerStatus)
        if (dialerStatus == "False"):
            print("Dialer inactive, starting.")
            update_config('activeDialer', "True", DIALER_DEPLOYMENT)
            print(launchDialer(SFN_ARN,ApplicationId,CampaignId))

    return {
        'statusCode': 200,
        'queuedContacts': index,
        'errorContacts': errors
    }

def get_endpoint_data(endpoint):
    
    userDetails={
        'custID': endpoint['User'].get('UserId',None),
        'phone': endpoint.get('Address',None),
        'attributes':{}
        }
    
    for attribkey in endpoint['Attributes'].keys():
        if len(endpoint['Attributes'][attribkey])>0:
            userDetails['attributes'][attribkey] = endpoint['Attributes'][attribkey][0]
        else:
            userDetails['attributes'][attribkey] = None
	
    if (userDetails['phone']):
        return(userDetails)
    else:
        return None

def launchDialer(sfnArn,ApplicationId,CampaignId):
    sfn = boto3.client('stepfunctions')
    inputData={
        'ApplicationId':ApplicationId,
        'CampaignId' : CampaignId
        }
    response = sfn.start_execution(
    stateMachineArn=sfnArn,
    input = json.dumps(inputData)
    )
    return response