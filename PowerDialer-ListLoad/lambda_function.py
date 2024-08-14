##Add S3 file contacts to queue
import json
import os
import boto3
import datetime
from botocore.exceptions import ClientError
from powerdialer import get_config
import re


sfn = boto3.client('stepfunctions')


SQS_URL = os.environ['SQS_URL']
DIALER_DEPLOYMENT= os.environ['DIALER_DEPLOYMENT']
SFN_ARN = os.environ['SFN_ARN']
CUSTOMER_PROFILES_DOMAIN = os.environ['CUSTOMER_PROFILES_DOMAIN']
NO_CALL_STATUS = os.environ['NO_CALL_STATUS'].split(",")
VALIDATE_PROFILE = os.environ['VALIDATE_PROFILE']



def lambda_handler(event, context):
    print(event)
    countrycode = get_config('countrycode', DIALER_DEPLOYMENT)
    s3fileName=event['BatchInput']['bucket']
    
    items = []
    for item_data in event['Items']:
        item = flatten_keys(item_data)
        #try:
        
        if (VALIDATE_PROFILE):
            disposition = check_valid_disposition(countrycode+item['Address'],CUSTOMER_PROFILES_DOMAIN)
            if(disposition):
                print("Accepting calls")
                items.append(pack_entry(item,countrycode,s3fileName))
            else:
                print("No call flag")
                items.append(pack_entry(item,countrycode,s3fileName))
        else:
            print("No validation, queuing")
            items.append(pack_entry(item,countrycode,s3fileName))
    
        #except Exception as e:
        #    print("Failed checking profile")
        #    print(e)
    
    response = queue_contacts(items,SQS_URL)
        

    return {
        'statusCode': 200,
        'queudContacts':response
    }

def get_template(template):
  try:
    response = pinpointClient.get_voice_template(
      TemplateName=template
    )
  except Exception as e:
    print("Error retrieving template")
    print(e)
    return False
  else:
    return response['VoiceTemplateResponse']['Body']


def check_valid_disposition(phoneNumber,customerProfileDomain):
    cpclient = boto3.client('customer-profiles')
    
    cp = cpclient.search_profiles(DomainName=customerProfileDomain,KeyName='_phone',Values=['+'+phoneNumber])

    if(len(cp['Items']) and 'Attributes' in cp['Items'][0] and 'callDisposition' in cp['Items'][0]['Attributes']):
        print(cp['Items'][0]['Attributes']['callDisposition'])
        if(cp['Items'][0]['Attributes']['callDisposition'] not in NO_CALL_STATUS):
            return True
        else:
            return False
    else:
        print("No call disposition assigned")
        return True

def queue_contacts(entries,sqs_url):
    sqs = boto3.client('sqs')
    try:
        response = sqs.send_message_batch(
            QueueUrl=sqs_url,
            Entries=entries
        )
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
        return len(response['Successful'])
        


def pack_entry(item,countrycode,s3fileName):
    attributes={
      'campaignId': datetime.datetime.now().isoformat(),
      'applicationId': 'S3FileImported',
      'campaignName': s3fileName
      }  
   
    attributes.update(item)
    return {
    'Id': item['UserId'],
    'MessageBody': '+' + countrycode + item['Address'],
    'MessageAttributes': {
                'custID': {
                    'DataType': 'String',
                    'StringValue': item['UserId']
                },
                'phone': {
                    'DataType': 'String',
                    'StringValue': '+' + countrycode + item['Address']
                },
                'attributes': {
                    'DataType': 'String',
                    'StringValue': json.dumps(item)
                }
        }
    }

def flatten_keys(item_data):
    transformed_data = {}
    for key, value in item_data.items():
        if '.' in key:
            new_key = key.split('.')[-1]
            transformed_data[new_key] = value
        else:
            transformed_data[key] = value
    return transformed_data