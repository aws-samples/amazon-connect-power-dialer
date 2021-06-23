##getConfig Function
import json
import boto3
import os
from powerdialer import scan_config
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print(event)
    config = scan_config(event["Input"]["config"]["dialerconfigtable"])
    return config
