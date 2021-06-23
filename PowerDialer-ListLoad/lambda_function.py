##dialer list laoding Function
import json
import boto3
import os
import csv
from powerdialer import get_config, upload_dial_record, update_config

from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print(event)
    configTable = os.environ['CONFIG_TABLE']
    dialerList = get_config('table-dialerlist', configTable)
    bucket = get_config('iobucket', configTable)
    fileKey = get_config('inputfile', configTable)
    
    s3_resource = boto3.resource('s3')
    s3_object = s3_resource.Object(bucket, fileKey)
    data = s3_object.get()['Body'].read().decode('utf-8').splitlines()
    
    lines = csv.reader(data)
    next(lines) #Skips Header
    index = 1
    for line in lines:
        calleeContacts = [
            {
              "callAttempted": False,
              "invalidNumber": False,
              "phone": line[1],
              "successfulConnection": False
            }
          ]
        upload_dial_record(index,line[0],calleeContacts, dialerList)
        index +=1
    update_config('totalRecords', str(index-1), configTable)
    return "Succesfully loaded: " + str(index-1) + " total records."
