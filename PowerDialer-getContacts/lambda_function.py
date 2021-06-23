##getContacts Function
import json
import boto3
import os
from powerdialer import get_config, get_callee, update_dial_list, update_config
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print(event)
    DIALER_CONFIG_TABLE=event['config']['dialerconfigtable']
    DIALER_LIST_TABLE= event['params']['table-dialerlist']
    
    availAgents = int(event['availAgents'])
    contacts = []
    responseIndex = 0
    totalRecords = int(event['params']['totalRecords'])
    print("Total Records: " + str(totalRecords))



    index = int(get_config('dialIndex',DIALER_CONFIG_TABLE))
    print("dialIndex: " + str(index))
    
    endOfList = True
    #Find the next phone in contact that has not been called.
    while(index<= totalRecords and responseIndex < availAgents):
        print("responseIndex: " + str(responseIndex))
        callee = get_callee(index, DIALER_LIST_TABLE)
        calleeContacts=callee['contacts']
        nextContactIndex = next((indx for (indx, d) in enumerate(calleeContacts) if d["callAttempted"] == False), None)
        if(nextContactIndex!=None):
            calleeContacts[nextContactIndex]['callAttempted']=True
            update_dial_list(index, 'contacts',calleeContacts, DIALER_LIST_TABLE)
            print('Fetched: ')
            print('CustID: ' + callee['custID'])
            responseIndex+= 1
            contacts.append(dict([('custID',callee['custID']),('index', index),('phone',calleeContacts[nextContactIndex]['phone'])]))
            
            endOfList = False
            #return contactResponse
        else:
            index += 1
            print('No more contacts available for callee, increasing index:')
            print("dialIndex: " + str(index))
            if(index<=totalRecords):
                update_config('dialIndex', index, DIALER_CONFIG_TABLE)
                #activeDialer = get_config('activeDialer',DIALER_CONFIG_TABLE)
            else:
                print("No more callees")
                #update_config('activeDialer', False, DIALER_CONFIG_TABLE)
                endOfList = True
                contactResponse ={"EndOfList": True}
                #return contactResponse

    contactResponse = dict([("EndOfList",endOfList),("contacts",contacts)])
    print(contactResponse)
    return contactResponse
