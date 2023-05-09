##getConfig Function
import json
import boto3
import os

def lambda_handler(event, context):
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    config=get_parameters(DIALER_DEPLOYMENT)
    return config
    
def get_parameters(deployment):
    ssm=boto3.client('ssm')
    try:
        ssmresponse = ssm.get_parameters_by_path(Path='/connect/dialer/'+deployment+'/',Recursive=True)

    except:
        return None
    else:
        config={}
        for parameter in ssmresponse['Parameters']:
            config[parameter['Name'].split("/")[-1]]=parameter['Value']
        return config


    