##dialer
import json
import boto3
import time
import random
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError


    
def delete_contact(receipt,sqs_url):
    sqs = boto3.client('sqs')
    try:
        sqs.delete_message(
        QueueUrl=sqs_url,
        ReceiptHandle=receipt
        )
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
        return True


def save_results(data,partition,streamName):
    firehose = boto3.client('firehose')
    try:
        response = firehose.put_record(
            DeliveryStreamName=streamName,
            Record={'Data': json.dumps(data)}
        )
        
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
        return response


def queue_contact(custID,phone,attributes,sqs_url):
    sqs = boto3.client('sqs')
    try:
        response = sqs.send_message(
            QueueUrl=sqs_url,
            MessageAttributes={
                'custID': {
                    'DataType': 'String',
                    'StringValue': custID
                },
                'phone': {
                    'DataType': 'String',
                    'StringValue': phone
                },
                'attributes': {
                    'DataType': 'String',
                    'StringValue': json.dumps(attributes)
                }
            },
            MessageBody=(
                phone
            )
        )
    except ClientError as e:
        print(e.response['Error'])
        return False
    else:
        return response['MessageId']

def upload_dial_record(dialIndex,custID,phone,attributes, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    
    try:
        response = table.update_item(
            Key={
                'seqID': dialIndex
            }, 
            UpdateExpression='SET #item = :newState, #item2 = :newState2,#item3 = :newState3,#item4 = :newState4,#item5 = :newState5,#item6 = :newState6',  
            ExpressionAttributeNames={
                '#item': 'custID',
                '#item2': 'phone',
                '#item3': 'attributes',
                '#item4': 'callAttempted',
                '#item5': 'invalidNumber',
                '#item6': 'successfulConnection'
            },
            ExpressionAttributeValues={
                ':newState': custID,
                ':newState2': phone,
                ':newState3': attributes,
                ':newState4': False,
                ':newState5': False,
                ':newState6': False
            },
            ReturnValues="UPDATED_NEW")

        print (response)
    except Exception as e:
        print (e)
    else:
        return response

def place_call(phoneNumber, contactFlow,connectID,queue,attributes):
    connect_client = boto3.client('connect')
    retry_count = 0
    response = False
    while retry_count < 4:
        try:
          if(len(attributes)>0):
            response = connect_client.start_outbound_voice_contact(
                  DestinationPhoneNumber=phoneNumber,
                  ContactFlowId=contactFlow,
                  InstanceId=connectID,
                  QueueId=queue,
                  Attributes=attributes,
                  ClientToken=attributes['campaignId']+'-'+attributes['endpointId'],
                  )
          else:
                response = connect_client.start_outbound_voice_contact(
                  DestinationPhoneNumber=phoneNumber,
                  ContactFlowId=contactFlow,
                  InstanceId=connectID,
                  ClientToken=attributes['campaignId']+'-'+attributes['endpointId'],
                  QueueId=queue
                  )
        except ClientError as error:
            print(error)
            if error.response['Error']['Code'] == 'TooManyRequestsException':
                print("TooManyRequestsException, waiting.")
                retry_count += 1
                delay = exponential_backoff(retry_count)
                time.sleep(delay)
                continue
            else:
                response = False
        finally:
            break

    return response

def exponential_backoff(retry_count, base_delay=1, max_delay=32):
    delay = min(base_delay * (2 ** retry_count), max_delay)
    jitter = random.uniform(0, 0.1)
    return delay + jitter


def updateActiveDialing(contactId, token, phone, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    timestamp = str(datetime.now())
    timetolive = 24*60*60 + int(time.time())

    try:
        response = table.update_item(
            Key={
                'contactId': contactId
            }, 
            UpdateExpression='SET #v1 = :val1, #v2 =:val2,#v3=:val3,#v4=:val4',  
            ExpressionAttributeNames={
                '#v1': 'token',
                '#v2': 'phone',
                '#v3': 'timestamp',
                '#v4': 'TimeToLive',
            },  
            ExpressionAttributeValues={
                ':val1': token,
                ':val2': phone,
                ':val3': timestamp,
                ':val4': timetolive
                
            },
            ReturnValues="UPDATED_NEW"
        )

    except Exception as e:
        print (e)

    else:
        return response

def get_config(parameter,deployment):
    try:
        ssm=boto3.client('ssm')
        ssmresponse = ssm.get_parameter(
        Name='/connect/dialer/'+deployment+'/'+parameter,
        )
    except:
        return None
    else:
        return ssmresponse['Parameter']['Value']

def update_dial_list(dialIndex, dialAttribute, dialValue, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    
    try:
        response = table.update_item(
            Key={
                'seqID': dialIndex
            }, 
            UpdateExpression='SET #item = :newState',  
            ExpressionAttributeNames={
                '#item': dialAttribute
            },
            ExpressionAttributeValues={
                ':newState': dialValue
            },
            ReturnValues="UPDATED_NEW")
        print (response)
    except Exception as e:
        print (e)
    else:
        return response

def update_config(parameter,value,deployment):
    ssm=boto3.client('ssm')
    try:
        ssmresponse = ssm.put_parameter(Name='/connect/dialer/'+deployment+'/'+parameter,Value=value,Overwrite=True)
    except:
        return False
    else:
        return True

def get_callee(index, table):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(table)
    try:
        response = table.query(
            KeyConditionExpression=Key('seqID').eq(index)
        )
    except:
        return False
    else:
        return response['Items'][0]

def get_total_records(table):
    
    client = boto3.client('dynamodb')
    response = client.describe_table(TableName=table)
    return(response['Table']['ItemCount'])

def get_token(id, table):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(table)
    response = table.query(
        KeyConditionExpression=Key('contactId').eq(id)
    )
    if (response['Count']): token = response['Items'][0]['token']
    else: token = None
    return token

def remove_contactId(id,table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)

    try:
        response = table.delete_item(
            Key={
                'contactId': id
            }
        )
    except Exception as e:
        print (e)
    else:
        return response

def sendSuccessToken(token,id):
        sfn = boto3.client('stepfunctions')
        response = sfn.send_task_success(
            taskToken=token,
            output='{"Payload": {"callAttempt":"callAttemptFailed", "contactId":"' + str(id) + '","validNumber":"True"}}'
        )
        return response

def update_call_attributes(customer_id,attributes,customerProfileDomain):
    cpclient = boto3.client('customer-profiles')

    try:
        cp = cpclient.search_profiles(DomainName=customerProfileDomain,KeyName='_phone',Values=[phoneNumber])
        if(len(cp['Items'])):
            response = cpclient.update_profile(
            DomainName=customerProfileDomain,
            ProfileId=cp['Items'][0]['ProfileId'],
            Attributes=attributes
            )
            print(f'Perfil del cliente actualizado correctamente: {response}')
            return response

    except ClientError as e:
        print(f'Error updating profile: {e}')
        return False


def get_call_preferences(phoneNumber,customerProfileDomain):
    cpclient = boto3.client('customer-profiles')
    try:
        cp = cpclient.search_profiles(DomainName=customerProfileDomain,KeyName='_phone',Values=['+'+phoneNumber])
    except ClientError as e:
        print(f'Error searching profile: {e}')
        return None
    else:
        print(cp['Items'])
        if(len(cp['Items'])):
            return cp['Items'][0].get('Attributes',None)
        else:
            return None