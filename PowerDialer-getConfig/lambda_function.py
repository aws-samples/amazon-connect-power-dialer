##getConfig Function
import json
import boto3
import os

ssm=boto3.client('ssm')

def lambda_handler(event, context):
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    config=get_parameters(DIALER_DEPLOYMENT)
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
                config[parameter['Name'].split("/")[-1]]=parameter['Value']
            
            next_token = ssmresponse.get('NextToken')

            if not next_token:
                break
            
    except:
        print("Error getting config")
        return None
    else:
        return config