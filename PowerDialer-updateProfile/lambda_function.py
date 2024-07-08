##updateProfile, requires attributes {'Key':'Value'}
import json
import boto3
import os
from powerdialer import get_call_preferences,update_call_attributes
from botocore.exceptions import ClientError

CUSTOMER_PROFILES_DOMAIN = os.environ('CUSTOMER_PROFILES_DOMAIN')

def lambda_handler(event, context):
    print(event)
    
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    contactPhone = str(event['Details']['ContactData']['CustomerEndpoint'])
    attributes= event['Details']['Parameters'].get('attributes',False)
    if attributes:
        print(update_call_attributes(contactPhone,attributes,CUSTOMER_PROFILES_DOMAIN))
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }