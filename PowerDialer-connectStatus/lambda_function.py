#Get Connect Status
import json
import boto3
import os
import datetime
import pytz

connect_client = boto3.client('connect')
ssm=boto3.client('ssm')

def lambda_handler(event, context):

    connect_id=event['params']['connectid'] 
    queueid=event['params']['queue']
    
    return {"workingHours":on_working_hours(connect_id, queueid), "queueEnabled":is_queue_enabled(connect_id, queueid)}


def is_queue_enabled(instanceId, queueId):
    response = connect_client.describe_queue(
    InstanceId=instanceId,
    QueueId=queueId
    )
    
    if(response['Queue']['Status']=='ENABLED'):
        return "True"
    else:
        return "False"
def on_working_hours(instanceId, queueId):
    queue = connect_client.describe_queue(
        InstanceId=instanceId,
        QueueId=queueId
        )
        
    hours = connect_client.describe_hours_of_operation(
        InstanceId=instanceId,
        HoursOfOperationId=queue['Queue']['HoursOfOperationId']
        )
        
    timezone = pytz.timezone(hours['HoursOfOperation']['TimeZone'])    
    today = datetime.datetime.now(timezone).strftime('%A').upper()
    current_time = datetime.datetime.now(timezone).time()


    for entry in hours['HoursOfOperation']['Config']:
        if entry['Day'] == today:
            start_time = datetime.time(entry['StartTime']['Hours'], entry['StartTime']['Minutes'])
            end_time = datetime.time(entry['EndTime']['Hours'], entry['EndTime']['Minutes'])
            if start_time <= current_time < end_time or start_time == end_time:
                response = "True"
                break
        else:
            response = "False"
    return response