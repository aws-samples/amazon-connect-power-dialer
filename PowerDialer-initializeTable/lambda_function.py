from __future__ import print_function
from crhelper import CfnResource
import logging
import boto3

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL', sleep_on_delete=120, ssl_verify=None)

try:
    dynamodb = boto3.resource('dynamodb')
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    def update_config(attribute, value, table):
        try:
            table = dynamodb.Table(table)
            response = table.update_item(
                Key={
                    'parameter': attribute
                }, 
                UpdateExpression='SET #v = :val',  
                ExpressionAttributeNames={
                    '#v': 'currentValue'
                },  
                ExpressionAttributeValues={
                    ':val': value
                },
                ReturnValues="UPDATED_NEW"
            )
    
        except Exception as e:
            print (e)
        else:
            return response
            
    logger.info("Got Create")
    configTable = event['ResourceProperties']['CONFIG_TABLE']
    activeDialingTable = event['ResourceProperties']['ACTIVE_DIALING_TABLE']
    dialerList = event['ResourceProperties']['DIALER_LIST']
    iobucket = event['ResourceProperties']['IOBUCKET']

    update_config('table-dialerlist', dialerList, configTable)
    update_config('table-activedialing', activeDialingTable, configTable)
    update_config('table-dialerlist', dialerList, configTable)
    update_config('iobucket', iobucket, configTable)
    update_config('totalRecords', '0', configTable)
    update_config('connectid', 'Replace with connectid', configTable)
    update_config('contactflow', 'Replace with  contactflow', configTable)
    update_config('queue', 'Replace with  queue', configTable)
    update_config('inputfile', 'Replace with dialing list filename', configTable)
    
    helper.Data.update({"test": "testdata"})

    if not helper.Data.get("test"):
        raise ValueError("this error will show in the cloudformation events log and console.")
    
    return "MyResourceId"


@helper.update
def update(event, context):
    logger.info("Got Update")



@helper.delete
def delete(event, context):
    logger.info("Got Delete")



@helper.poll_create
def poll_create(event, context):
    logger.info("Got create poll")

    return True


def lambda_handler(event, context):
    helper(event, context)