##Dialing Results Load to S3
import json
import boto3
import os
import csv

from powerdialer import get_config
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    dynamodb = boto3.client('dynamodb')
    print(event)
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    dialerList = get_config('table-dialerlist', DIALER_DEPLOYMENT)
    bucket = get_config('ResultsBucket', DIALER_DEPLOYMENT)
    
    response = dynamodb.scan(
        TableName=dialerList,
        Select='ALL_ATTRIBUTES')
    data = response['Items']
    
    while 'LastEvaluatedKey' in response:
        response = dynamodb.scan(
            TableName=dialerList,
            Select='ALL_ATTRIBUTES',
        ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
    
    prettyData = []
    for item in data:
        prettyData.append(remove_types(item))
    print(prettyData)
    
    datajson = json.dumps(prettyData, ensure_ascii=False)
    response = s3_client.put_object(Body=datajson,  
                                    Bucket=bucket,
                                    Key='results/dialingResults.json',
                                    ACL="bucket-owner-full-control")
    return {'Status':'OK'}

def remove_types(ddbjson):
    result = {}
    for key, value in ddbjson.items():
        if isinstance(value, dict):
            if len(value) == 1:
                new_key, new_value = list(value.items())[0]
                if new_key == 'BOOL':
                    result[key] = new_value
                elif new_key == 'N' and new_value.isdigit():
                    result[key] = int(new_value)
                elif new_key == 'S':
                    result[key] = new_value
                else:
                    result.update(remove_types(value))
            else:
                result.update(remove_types(value))
        else:
            result[key] = value
    return result