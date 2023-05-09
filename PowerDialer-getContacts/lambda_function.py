##getContacts Function
import json
import boto3
import os
from powerdialer import get_config, get_callee, update_dial_list, update_config
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print(event)
    DIALER_DEPLOYMENT = os.environ['DIALER_DEPLOYMENT']
    DIALER_LIST_TABLE = get_config('table-dialerlist', DIALER_DEPLOYMENT)
    
    availAgents = int(event['availAgents'])
    contacts = []
    responseIndex = 0
    totalRecords = int(event['params']['totalRecords'])
    print("Total Records: " + str(totalRecords))



    index = int(get_config('dialIndex',DIALER_DEPLOYMENT))
    print("dialIndex: " + str(index))
    
    endOfList = "True"
    #Find the next phone in contact that has not been called.
    while(index<= totalRecords and responseIndex < availAgents):
        print("responseIndex: " + str(responseIndex))
        callee = get_callee(index, DIALER_LIST_TABLE)
        
        #Validates it has not been called.
        #nextContactIndex = next((indx for (indx, d) in enumerate(calleeContacts) if d["callAttempted"] == False), None)
        if(callee!=None and callee['callAttempted']==False):
            
            update_dial_list(index, 'callAttempted',True, DIALER_LIST_TABLE)
            print('Fetched: ')
            print('CustID: ' + callee['custID']+':'+callee['phone'])
            responseIndex+= 1
            contacts.append(dict([('custID',callee['custID']),('index', index),('phone',callee['phone']),('attributes',callee['attributes'])]))
            endOfList = "False"
            #return contactResponse
        else:
            index += 1
            print('No more contacts available for callee, increasing index:')
            print("dialIndex: " + str(index))
            if(index<=totalRecords):
                update_config('dialIndex', index, DIALER_DEPLOYMENT)
                
            else:
                print("No more callees")
                endOfList = "True"

    contactResponse = dict([("EndOfList",endOfList),("contacts",contacts)])
    print(contactResponse)
    return contactResponse
