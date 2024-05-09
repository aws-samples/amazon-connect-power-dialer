#Get Connect Status
import json
import boto3
import botocore
import os
import datetime
import pytz
import random
import time

connect_client = boto3.client('connect')
ssm=boto3.client('ssm')

def lambda_handler(event, context):

    connect_id=event['params']['connectid'] 
    queueid=event['params']['queue']
    response = queue_status(connect_id, queueid)
    response['availableAgents']=get_available_agents(connect_id,queueid)
    print(response)
    return response


def queue_status(instanceId, queueId):
    retry_count = 0
    hours={}
    queue={}
    response={}
    while retry_count < 3:
        try:
            queue = connect_client.describe_queue(InstanceId=instanceId,QueueId=queueId)
            
        except botocore.exceptions.ClientError as error:
            print(error)
            if error.response['Error']['Code'] == 'TooManyRequestsException':
                print("TooManyRequestsException, waiting.")
                retry_count += 1
                delay = exponential_backoff(retry_count)
                time.sleep(delay)
                continue
            else:
                raise error
        finally:
            break

    if(queue['Queue']['Status']=='ENABLED'):
        response['queueEnabled']='True'
    else:
        response['queueEnabled']= "False"

    retry_count = 0
    while retry_count < 3:
        try:
            hours = connect_client.describe_hours_of_operation(InstanceId=instanceId,HoursOfOperationId=queue['Queue']['HoursOfOperationId'])
        except botocore.exceptions.ClientError as error:
            print(error)
            if error.response['Error']['Code'] == 'TooManyRequestsException':
                print("TooManyRequestsException, waiting.")
                retry_count += 1
                delay = exponential_backoff(retry_count)
                time.sleep(delay)
            else:
                raise error
        finally:
            break

    timezone = pytz.timezone(hours['HoursOfOperation']['TimeZone'])    
    today = datetime.datetime.now(timezone).strftime('%A').upper()
    current_time = datetime.datetime.now(timezone).time()


    for entry in hours['HoursOfOperation']['Config']:
        if entry['Day'] == today:
            start_time = datetime.time(entry['StartTime']['Hours'], entry['StartTime']['Minutes'])
            end_time = datetime.time(entry['EndTime']['Hours'], entry['EndTime']['Minutes'])
            if start_time <= current_time < end_time or start_time == end_time:
                response['workingHours'] = "True"
                break
        else:
            response['workingHours'] = "False"
    return response

def exponential_backoff(retry_count, base_delay=1, max_delay=32):
    delay = min(base_delay * (2 ** retry_count), max_delay)
    jitter = random.uniform(0, 0.1)
    return delay + jitter

def get_available_agents(connectid,queue):
    
    connect_client = boto3.client('connect')
    response = connect_client.get_current_metric_data(
    InstanceId=connectid,
    Filters={
        'Queues': [
            queue,
        ],
        'Channels': [
            'VOICE',
        ]
    },
    CurrentMetrics=[
        {
            'Name': 'AGENTS_ONLINE',
            'Unit': 'COUNT'
        },
    ],
)
    #print("Available Agents Metrics :" + str(response['MetricResults']))
    
    if(response['MetricResults']):
        availAgents = int(response['MetricResults'][0]['Collections'][0]['Value'])
    else: 
        availAgents =0
    return availAgents