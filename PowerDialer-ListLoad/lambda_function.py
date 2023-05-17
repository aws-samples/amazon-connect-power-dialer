##dialer list loading Function
import json
import boto3
import os
import csv
from powerdialer import get_config, upload_dial_record, update_config, queue_contact
from urllib.parse import unquote

from boto3.dynamodb.conditions import Key

client = boto3.client('events')

def lambda_handler(event, context):
    print(event)
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    SQS_URL= os.environ['SQS_URL']

    #dialerList = get_config('table-dialerlist', DIALER_DEPLOYMENT) ##Previous approach
    
    index = 1
    try:
        for rec in event['Records']:
            # get file key from event
            fileKey = unquote(unquote(rec['s3']['object']['key']))
            bucket = rec['s3']['bucket']['name']
            
            #s3 = boto3.client('s3')
            s3_resource = boto3.resource('s3')
            
            s3_object = s3_resource.Object(bucket, fileKey)
            data = s3_object.get()['Body'].read().decode('utf-8').splitlines()

            
            requiredFields = set(['phone', 'custID'])
    
            lines = csv.DictReader(data)
            index = 1
            for line in lines:
                if all(item in line for item in requiredFields):
                    attributes = {}
                    for key in line.keys():
                        if (key not in requiredFields):
                            attributes[key]=line[key]

                    queue_contact(line['custID'],line['phone'], attributes,SQS_URL)
                    #upload_dial_record(index,line['custID'],line['phone'], attributes,dialerList)
                    index +=1            
    
            update_config('totalRecords', str(index-1), DIALER_DEPLOYMENT)
            update_config('dialIndex', str(1), DIALER_DEPLOYMENT)
    
    except Exception as e:
        print(e)
        raise e
    
    return "Succesfully loaded: " + str(index-1) + " total records."


get_time_expression(hour,minutes,tzshift):
    utchour = int(hour) + int(tzshift)
    schedule = 'cron(' + minutes + ' ' + str(utchour) + ' ' + '? * MON-FRI *)'
    print(schedule)
    return (schedule)