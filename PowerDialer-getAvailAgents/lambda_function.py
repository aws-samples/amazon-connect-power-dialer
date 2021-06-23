#Get Available Agents in Queue
import json
import boto3
import os


def lambda_handler(event, context):
    print(event)
    
    CONNECT_INSTANCE_ID=event['params']['connectid'] 
    CONNECT_QUEUE_ID=event['params']['queue']
    
    connect_client = boto3.client('connect')
    response = connect_client.get_current_metric_data(
    InstanceId=CONNECT_INSTANCE_ID,
    Filters={
        'Queues': [
            CONNECT_QUEUE_ID,
        ],
        'Channels': [
            'VOICE',
        ]
    },
    CurrentMetrics=[
        {
            'Name': 'AGENTS_AVAILABLE',
            'Unit': 'COUNT'
        },
    ],
)
    print("Available Agents Metriics :" + str(response['MetricResults']))
    
    if(response['MetricResults']):availAgents = int(response['MetricResults'][0]['Collections'][0]['Value'])
    else: availAgents =0
    return {"availAgents":availAgents}
