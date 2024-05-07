##getConfig Function
import json
import boto3
import os

ssm=boto3.client('ssm')

def lambda_handler(event, context):
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    config=get_parameters(DIALER_DEPLOYMENT)
    config['concurrentCalls'] = min(int(get_available_agents(config['connectid'],config['queue'])),int(config['concurrentCalls']))
    config['dialerThreads']= [0]*int(config['concurrentCalls'])
    return config
    
def get_parameters(deployment):
    
    config={}
    next_token = None

    try:
        while True:
            if next_token:
                ssmresponse = ssm.get_parameters_by_path(Path='/connect/dialer/'+deployment+'/',NextToken=next_token)
            else:
                ssmresponse = ssm.get_parameters_by_path(Path='/connect/dialer/'+deployment+'/')
            for parameter in ssmresponse['Parameters']:
                if(parameter['Value'].isnumeric()):
                   config[parameter['Name'].split("/")[-1]]=int(parameter['Value'])
                else:
                   config[parameter['Name'].split("/")[-1]]=parameter['Value']
            next_token = ssmresponse.get('NextToken')

            if not next_token:
                break

    except:
        print("Error getting config")
        return None
    else:
        return config


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