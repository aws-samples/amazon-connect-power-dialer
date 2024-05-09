##Add Pinpoint contacts to queue
import json
import os
import boto3
import datetime
from botocore.exceptions import ClientError
import re
from powerdialer import queue_contact,update_config,get_config

pinpointClient = boto3.client('pinpoint')
sfn = boto3.client('stepfunctions')


SQS_URL = os.environ['SQS_URL']
DIALER_DEPLOYMENT= os.environ['DIALER_DEPLOYMENT']
SFN_ARN = os.environ['SFN_ARN']
countrycode = get_config('countrycode', DIALER_DEPLOYMENT)
isocountrycode = get_config('isocountrycode', DIALER_DEPLOYMENT)


def lambda_handler(event, context):
    print(event)
    endpoints=event['Endpoints']
    count=0
    errors=0
    custom_events_batch = {}
    ApplicationId= event['ApplicationId']
    CampaignId= event['CampaignId']
    for key in endpoints.keys():
        
        user = event['Endpoints'][key]
        campaignDetails = get_campaign_details(event['ApplicationId'],event['CampaignId'])
        attributes={
              'campaignId': event['CampaignId'],
              'applicationId': event['ApplicationId'],
              'campaignName': campaignDetails['CampaignName'],
              'segmentName': campaignDetails['SegmentName'],
              'campaingStartTime': campaignDetails['StartTime'],
              'endpointId':key
              }  
        
        if ('Data' in event):
            templateName = event['Data']
            templateMessage = get_template(templateName)
        else:
            templateMessage=False
        
        if(templateMessage):
            body = get_message(templateMessage,user)
            attributes['prompt']=body
            data = get_endpoint_data(endpoints[key])
            if('attributes' in data):
                attributes.update(data['attributes'])
            
            if(data):
              validated_number = validate_endpoint(data['phone'],countrycode,isocountrycode)
              
              if(validated_number and 'PhoneType' in validated_number and validated_number['PhoneType']!='INVALID'):
                attributes['phonetype']=validated_number['PhoneType']
                try:
                  print("Queuing",'+'+countrycode+data['phone'],data['custID'],attributes)
                  queue_contact(data['custID'],'+'+countrycode+data['phone'],attributes,SQS_URL)
                except Exception as e:
                    print("Failed to queue")
                    print(e)
                else:
                    #custom_events_batch[key] = create_success_custom_event(key, CampaignId, body)
                    count+=1
              else:
                print("Invalid phone number:" + str(data['phone']))
                #custom_events_batch[key] = create_failure_custom_event(key, CampaignId, "Invalid phone")
                
                errors+=1
        else:
            print("Template returned blank")
            #custom_events_batch[key] = create_failure_custom_event(key, CampaignId, "Template not found")
            #pause_campaign(ApplicationId,CampaignId)
        
    if(count):
        print("Contacts added to queue, validating dialer status.")
        dialerStatus = get_config('activeDialer', DIALER_DEPLOYMENT)
        sfStatus = int(check_sf_executions(SFN_ARN))
        print('dialerStatus',dialerStatus)
        print('sfStatus',sfStatus)
        
        if (dialerStatus == "False" and sfStatus==0):
            print("Dialer inactive, starting.")
            print(launchDialer(SFN_ARN,ApplicationId,CampaignId))
        else:
            print("SF already started")    
    #send_results(event['ApplicationId'],custom_events_batch)

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

def check_sf_executions(sf_arn):
    response = sfn.list_executions(
    stateMachineArn=sf_arn,
    statusFilter='RUNNING'
    )
    
    return(len(response['executions']))

def launchDialer(sfnArn,ApplicationId,CampaignId):
    
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


def create_success_custom_event(endpoint_id, campaign_id, message):
    custom_event = {
        'Endpoint': {},
        'Events': {}
    }
    custom_event['Events']['voice_%s_%s' % (endpoint_id, campaign_id)] = {
        'EventType': 'queuing.success',
        'Timestamp': datetime.datetime.now().isoformat(),
        'Attributes': {
            'campaign_id': campaign_id,
            'message': (message[:195] + '...') if len(message) > 195 else message
        }
    }
    return custom_event

def create_failure_custom_event(endpoint_id, campaign_id, e):
    error = repr(e)
    custom_event = {
        'Endpoint': {},
        'Events': {}
    }
    custom_event['Events']['voice_%s_%s' % (endpoint_id, campaign_id)] = {
        'EventType': 'queuing.failure',
        'Timestamp': datetime.datetime.now().isoformat(),
        'Attributes': {
            'campaign_id': campaign_id,
            'error': (error[:195] + '...') if len(error) > 195 else error
        }
    }
    return custom_event

def send_results(application_id,events_batch):
    put_events_result = pinpointClient.put_events(
        ApplicationId=application_id,
        EventsRequest={
            'BatchItem': events_batch
        }
    )
    print(put_events_result)
def pause_campaign(application_id,campaign_id):
    try:
        response = pinpointClient.update_campaign(
        ApplicationId=application_id,
        CampaignId=campaign_id,
        WriteCampaignRequest={'IsPaused': True})
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
        return response