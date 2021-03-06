##Dialing Results Load to S3
import json
import boto3
import os

from powerdialer import get_config
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    dynamodb = boto3.client('dynamodb')
    print(event)
    configTable = event["config"]["dialerconfigtable"]
    dialerList = get_config('table-dialerlist', configTable)
    bucket = get_config('iobucket', configTable)
    
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
    
    
    datajson = json.dumps(data, ensure_ascii=False)
    response = s3_client.put_object(Body=datajson,  
                                    Bucket=bucket,
                                    Key='results/dialingResults.json',
                                    ACL="bucket-owner-full-control")

    return response