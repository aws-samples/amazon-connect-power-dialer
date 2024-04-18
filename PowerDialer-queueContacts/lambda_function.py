##Add Pinpoint contacts to queue
import json
import os
import boto3
from botocore.exceptions import ClientError
import re
from powerdialer import queue_contact,update_config,get_config

pinpointClient = boto3.client('pinpoint')

SQS_URL = os.environ['SQS_URL']
DIALER_DEPLOYMENT= os.environ['DIALER_DEPLOYMENT']
SFN_ARN = os.environ['SFN_ARN']
countrycode = '52'
isocountrycode = 'MX'


def lambda_handler(event, context):
    print(event)
    endpoints =event['Endpoints']
    count=0
    errors=0
    ApplicationId= event['ApplicationId']
    CampaignId= event['CampaignId']
    for key in endpoints.keys():
        templateName = event['Data']
        user = event['Endpoints'][key]
        
        templateMessage = get_template(templateName)
        body = get_message(templateMessage,user)
        campaignDetails = get_campaign_details(event['ApplicationId'],event['CampaignId'])

        attributes={
          'prompt': body,
          'campaignId': event['CampaignId'],
          'applicationId': event['ApplicationId'],
          'campaignName': campaignDetails['CampaignName'],
          'segmentName': campaignDetails['SegmentName'],
          'campaingStartTime': campaignDetails['StartTime'],
          'endpointId':key
          }
        data = get_endpoint_data(endpoints[key])
        
        if('attributes' in data):
          attributes.update(data['attributes'])
        if(data):
          validated_number = validate_endpoint(data['phone'],countrycode,isocountrycode)
          
          if(validated_number and 'PhoneType' in validated_number and validated_number['PhoneType']!='INVALID'):
            attributes['phonetype']=validated_number['PhoneType']
            try:
              print("Queuing",'+'+countrycode+data['phone'],data['custID'],attributes)
              queue_contact(data['custID'],'+'+countrycode+data['phone'],data['attributes'],SQS_URL)
            except Exception as e:
                print("Failed to queue")
                print(e)
            else:
                count+=1
          else:
            print("Invalid phone number:" + str(data['phone']))
            errors+=1
        
    if(count):
        print("Contacts added to queue, validating dialer status.")
        dialerStatus = get_config('activeDialer', DIALER_DEPLOYMENT)
        print(dialerStatus)
        if (dialerStatus == "False"):
            print("Dialer inactive, starting.")
            update_config('activeDialer', "True", DIALER_DEPLOYMENT)
            print(launchDialer(SFN_ARN,ApplicationId,CampaignId))

    return {
        'statusCode': 200,
        'queuedContacts': count,
        'errorContacts': errors
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

def get_endpoint_data(endpoint):
    userDetails={
        'phone': endpoint.get('Address',None),
        'attributes':{}
        }
        
    if ('UserId' in endpoint['User']):
        userDetails['custID'] = endpoint['User'].get('UserId',None)
        print("there is a UserId")
        
    if ('UserAttributes' in endpoint['User'] and endpoint['User']['UserAttributes']):
      for attribkey in endpoint['User']['UserAttributes'].keys():
          if len(endpoint['User']['UserAttributes'][attribkey])>0:
              userDetails['attributes'][attribkey] = endpoint['User']['UserAttributes'][attribkey][0]
          else:
              userDetails['attributes'][attribkey] = 'None'
  
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

def get_campaign_details(applicationid,campaignid):
  campaignResponse = pinpointClient.get_campaign(
      ApplicationId=applicationid,
      CampaignId=campaignid
    )
  segmentResponse = pinpointClient.get_segment(
      ApplicationId=applicationid,
      SegmentId=campaignResponse['CampaignResponse']['SegmentId']
    )
  campaignDetails = {
    "Creation": campaignResponse['CampaignResponse']['CreationDate'],
    "CampaignName": campaignResponse['CampaignResponse']['Name'],
    "StartTime" : campaignResponse['CampaignResponse']['Schedule']['StartTime'],
    "SegmentId":campaignResponse['CampaignResponse']['SegmentId'],
    "Timezone":campaignResponse['CampaignResponse']['Schedule']['Timezone'],
    "SegmentName":segmentResponse['SegmentResponse']['Name']
    }
  
  return campaignDetails

def get_message(text, data):
    def replace(match):
        key = match.group()[2:-2]  
        value = get_value(key, data)
        return str(value)

    def get_value(key, data):
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if isinstance(value, str):
                    value = value.strip("'")  
                elif isinstance(value, list):
                    value = " ".join(value)
            elif isinstance(value, list):
                value = value[0]
                if isinstance(value, str):
                    value = value.strip("'")
                elif isinstance(value, list):
                    value = " ".join(value)
            else:
                return None
        return value

    pattern = r'\{\{.*?\}\}'
    replaced_text = re.sub(pattern, replace, text)
    return replaced_text

def validate_endpoint(endpoint,countrycode,isocountrycode):
    try:
        response = pinpointClient.phone_number_validate(
        NumberValidateRequest={
        'IsoCountryCode': isocountrycode,
        'PhoneNumber': countrycode+endpoint
        })
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
      return response['NumberValidateResponse']
