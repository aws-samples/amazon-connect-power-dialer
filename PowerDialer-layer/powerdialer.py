##dialer
import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key


def upload_dial_record(dialIndex, custID, calleeContacts, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    
    try:
        response = table.update_item(
            Key={
                'seqID': dialIndex
            }, 
            UpdateExpression='SET #item = :newState, #item2 = :newState2',  
            ExpressionAttributeNames={
                '#item': 'custID',
                '#item2': 'contacts'
            },
            ExpressionAttributeValues={
                ':newState': custID,
                ':newState2': calleeContacts
            },
            ReturnValues="UPDATED_NEW")
        print (response)
    except Exception as e:
        print (e)
    else:
        return response

def place_call(phoneNumber, contactFlow,connectID,queue):
    connect_client = boto3.client('connect')
    try:
        response = connect_client.start_outbound_voice_contact(
            DestinationPhoneNumber=phoneNumber,
            ContactFlowId=contactFlow,
            InstanceId=connectID,
            QueueId=queue,
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

def get_config(configItem, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    response = table.query(
        KeyConditionExpression=Key('parameter').eq(configItem)
    )
    
    if (response['Items']): currentValue = response['Items'][0]['currentValue']
    else: currentValue = None
    return currentValue

def scan_config(table):
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.scan(TableName=table)
    config={}
    for item in response['Items']:
        parameterArr = list(item['parameter'].values())
        valueArr = list(item['currentValue'].values())
        config[parameterArr[0]] = valueArr[0]
    return config

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

def update_config(attribute, value, table):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table)
    
    try:
        response = table.update_item(
            Key={
                'parameter': attribute
            }, 
            UpdateExpression='SET #v = :val',  
            ExpressionAttributeNames={
                '#v': 'currentValue'
            },  
            ExpressionAttributeValues={
                ':val': value
            },
            ReturnValues="UPDATED_NEW"
        )

    except Exception as e:
        print (e)
    else:
        return response

def get_callee(index, table):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(table)
    response = table.query(
        KeyConditionExpression=Key('seqID').eq(index)
    )
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