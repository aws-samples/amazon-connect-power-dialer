##dialer
import json
import boto3
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
    try:
        if(len(attributes)>0):
            response = connect_client.start_outbound_voice_contact(
                DestinationPhoneNumber=phoneNumber,
                ContactFlowId=contactFlow,
                InstanceId=connectID,
                QueueId=queue,
                Attributes=attributes
                )
        else:
            response = connect_client.start_outbound_voice_contact(
                DestinationPhoneNumber=phoneNumber,
                ContactFlowId=contactFlow,
                InstanceId=connectID,
                ClientToken=attributes['campaignId']+'-'+attributes['endpointId'],
                QueueId=queue
                )
    except Exception as e:
        print(e)
        print("phone" + str(phoneNumber))
        response = None
    return response

def updateActiveDialing(contactId, token, phone, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    timestamp = str(datetime.now())
    try:
        response = table.update_item(
            Key={
                'contactId': contactId
            }, 
            UpdateExpression='SET #v1 = :val1, #v2 =:val2,#v3=:val3',  
            ExpressionAttributeNames={
                '#v1': 'token',
                '#v2': 'phone',
                '#v3': 'timestamp',
            },  
            ExpressionAttributeValues={
                ':val1': token,
                ':val2': phone,
                ':val3': timestamp
                
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