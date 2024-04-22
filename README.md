# Amazon Connect Power Dialer
04/21/24: Simplified dialing mechanism based on a single Step Function. Added attribute handling from Pinpoint list. Added ClientToken on start_outbound_voice_call to remove potential duplicate calls per campaign.

This project contains source code and supporting files for a serverless dialer to be used on top of an Amazon Connect instance.

The basic operation of the solution is based on the principle of a Power Dialer: New calls are placed once agents complete previous calls. Since calls are placed automatically, the inefficiencies and error-prone nature of manual dialing are mitigated; yet, since calls are initiated until agents become available, you can maintain the warm nature of person to person contacts (no wait time for end users when being contacted).
The general workflow for this solution is as follows:

![Workflow](/images/DialerOnConnect-Workflow.jpg "Workflow")

1.	This is based on Amazon Pinpoint, segments must be based on files including: ChannelType,Address,User.UserId. Additional attributes should be mapped under User.UserAttributes.XXX.
2.	A message template must be configured as part of Amazon Pinpoint. Attributes from the associated segment can be configured.
3.	A campaign is launched based on the custom channel, pointint to the queueContacts Lambda function.
4.	Contacts are queue on the SQS queue. The parameter concurrentCalls determines the number of simultaneous threads to initiate calling (this number should map expected agents). The dialer pulls contacts from the queue based on call concurrency.
5.	Calls are launched in parallel based on the number of concurrentCalls.
6.	Successful call connections are put in the configured queue.  
7.	Agent and contact activity are monitored so calls are initiated once Agents wrap up the active calls.
8.  System parameters are included under the /connect/dialer/<DEPLOYMENT>/ path.

The solution leverages Amazon Connect API start outbound voice API to place calls, triggered by AWS Lambda Functions and orchestrated with Step Functions. Lambda Functions are also used to pull configuration, read contacts from the dialing list table and monitor Amazon Connect events on a Amazon Kinesis Stream (from both Contact Trace Records and Agent Events). Finally, Amazon DynamoDB and Amazon Simple Storage Service are used for dialing list, configuration parameters storage and input/output space for dialing lists and results. 
Roles for the Lambda Functions and Step Functions State Machines are defined in AWS Identity and Access Management to limit access to specific resources. 

![Architecture](/images/DialerOnConnect-Architecture.jpg "Architecture")

## Deployed resources

The project includes a cloud formation template with a Serverless Application Model (SAM) transform to deploy resources as follows:

### Amazon S3
- Resultsbucket: Storage for campaign results.

### AWS Lambda functions

- dial: Places calls using Amazon Connect boto3's start_outbound_voice_contact method.
- getAvailAgents: Gets agents available in the associated queue.
- getConfig: Gets the configuration parameters from a DynamoDB table.
- getContacts: Gets contact phone numbers to dial from a DynamoDB table.
- queueContacts: Loads dialing list from the Amazon Pinpoint campaign.
- ProcessContactEvents: Processes Contact Events to determine when would the next call should be placed.
- SetDisposition: Process agent input based on a step by step guide contact flow to categorize calls.
- SaveResults: Generates a CSV file based from the dialing attempts.


### Step Functions

- DialerControlSF: Provides the general structure for the dialer. Pulls initial configuration and invokes parallel dialer executions to perform the dialing process.

### DynamoDB tables
- ActiveDialing: ContactIds to dialed contact relationship for contacts being dialed.

### System Manager Paramater Store Parameters
Configuration information is stored as parameters in System Manager Parameter Store. The following parameters require configuration to match Connect configuration.
- /connect/dialer/XXXX/connectid. Connect Instance Id (not ARN).
- /connect/dialer/XXXX/contactflow. Contact Flow Id (not ARN).
- /connect/dialer/XXXX/queue. Amazon Connect Outbound Queue (not ARN).

- /connect/dialer/XXXX/ResultsBucket. Output bucket for results. Populated at set up time.
- /connect/dialer/XXXX/activeDialer. On/Off switch for dialer opperation. Managed by State machines.
- /connect/dialer/XXXX/dialIndex. index position within list.
- /connect/dialer/XXXX/table-activedialing. Active numbers processing calls.
- /connect/dialer/XXXX/table-dialerlist. Complete dialing list.
- /connect/dialer/XXXX/totalRecords. Current number of records to be called.

### IAM roles
- ControlSFRole: Dialer Control Step Functions state Machine IAM role.
- ThreadSFRole: Dialer Thread Step Functions state Machine IAM role.
- PowerDialerLambdaRole: Lambda Functions IAM role.


## Prerequisites.
1. Amazon Connect Instance already set up.
2. AWS Console Access with administrator account.
3. Cloud9 IDE or AWS and SAM tools installed and properly configured with administrator credentials.
4. Configured project for Amazon Pinpoint.
5. Message templates and built segments in Pinpoint.

## Deploy the solution
1. Clone this repo.

`git clone https://github.com/aws-samples/amazon-connect-power-dialer`

2. Build the solution with SAM.

`sam build` 

if you get an error message about requirements you can try using containers.

`sam build -u` 


3. Deploy the solution.

`sam deploy -g`

SAM will ask for the name of the application (use "PowerDialer" or something similar) as all resources will be grouped under it;Connect parameters, concurrent calls and targeted country (Phone number digits and the 2 letter ISO country code); Region and a confirmation prompt before deploying resources, enter y.
SAM can save this information if you plan un doing changes, answer Y when prompted and accept the default environment and file name for the configuration.


## Configure Amazon Connect Agent Events and Contact Trace Records.


## Get Amazon Connect Configuration

As part of the configuration, you will need the deployed Amazon Connect Instance ID (referenced as connectid on the configuration parameters of this solution), a contact flow used for Outbound calling (referenced as contactflow on the configuration parameters of this solution) and the queue ID (referenced as queue):

1. Navigate to the Amazon Connect console.
2. Click on Access URL. This will open the Amazon Connect interface.
3. From the left panel, open the routing menu (it has an arrow splitting in three as an icon).
4. Click on contact flow. Select the Default outbound contact flow. Click on "show additional flow information".
5. Copy the associated ARN. You will need 2 items from that string the instance id and the contact flow id. The instance ID is the string following the first "/" after the word instance and up to the following "/".The contact flow ID is the string separated by the "/" following "contact-flow". Make note of this 2 strings (do not copy "/").
6. Navigate back to routing and pick queues. Select the queue you'll be using and click on show additional queue information.
7. Make note of the string separated by a "/" after the word queue on the ARN. Make sure you do not copy "/".
8. Make a test call to make sure you are able to start outbound calls. Log an agent on the Amazon CCP and have it set their status to Available.
9. From a command line terminal where you have already configured AWS Cli with administrator credentials, type:

`aws connect start-outbound-voice-contact --destination-phone-number <value> --contact-flow-id <value> --instance-id <value> --queue-id <value>`

Make sure you replace the values for contactflow, phone numberm, queue and instance id. A call should be placed and put in queue.

## Configure Dialer Parameters
This parameters are configured at solution deployment, modify only to change the initial configuration.
1. Navigate to the System Manager - Parameter Store console.
2. Modify the values for the following items. Note this items are case sensitive.

| parameter   | currentValue |
|----------|:-------------:|
| /connect/dialer/XXXX/connectid |  Connect instance ID |
| /connect/dialer/XXXX/contactflow |contactflow ID|
|/connect/dialer/XXXX/queue|Id of the Connect queue to be used|

## Setting Disposition Codes
As part of the deployment, a setDisposition Code function is created. This function will take contactId and attributes set on the dial phase to update the result on the dialing list table.
The step by step guide contact flow (file , available on the sample files allows for a sample option to generate status and invoke the setDisposition Lambda function to tag associated contacts.

### Deploy agent guide flow.
1. From the AWS Services Console, browse to the Amazon Connect service and add the setDisposition Lambda function in Flows->Lambda.
1. In the Amazon Connect administrator interface create a new contact flow and import the View-Dialer-DispositionCodes sample file. Validate all boxes are configured correctly, save and publish the flow.
1. Make a note of the contact flow id on the ARN for this contact flow.
1. Add a Set Contact Attributes block on the ContactFlow used for outbound calls, specify a user defined parameter for DefaultFlowForAgentUI and specify the contact flow id from the previous step.

## Campaign scheduling
As an alternative orchestration mechanism, an Eventbridge rule is created. 
An EventBridge rule is created as part of the deployment in the disabled state. From Eventbridge console browse to rules and select the <YOUR-STACK-NAME>CampaignLaunchSchedule rule.

1. Click on Edit.
2. Specify the required launch times for this campaign.
3. Keep the selected target DialerControlSF-XXXX.
4. Save changes and make sure to change the status of the rule to enabled.

## Operation
The solution relies on Step Functions as the main orchestation point and Lambda Functions as the processing units. To start a campaign, launch a campaign on Amazon Pinpoint with a custom channel and the queueContacts lambda function as target. The solution will create queue contacts and launch the dialer control state machine.

### Loading a dialing list. 
Alternatively to Pinpoint, to load a list, simply upload a CSV file (example is provided on file [sample-file](/sample-files/sample-load.csv "sample-file") ) to the input bucket. An automated event will trigger the processing Lambda Function to upload the records. Be aware large files might consume a lot of time and might timeout on the Labda Function.


#### Uploading the file 
1. Generate a CSV file with the same structure as the example.
3. Go to cloudformation and select the stack created for this application (it will have the same name as you specified as application name).
4. Browse to the resources tab.
5. Click on the link for the iobucket name, a new window will open showing the bucket.
6. Click on the upload file and uplaod the file you created.

### Launching a dialing job.
The process to start the dialing job is through the Power Dialer Control Step Function, initiate an execution to launch the dialing job or by means of scheduling recurring campaign.

1. Navigate to the StepFunctions console.
2. Pick the Control Step Machine, it should have a name similar to: "DialerControlSF-XXXXXXXX".
3. Click Start Execution. A "Start Execution Window" will open, click Start Execution once again. This will start the dialing job, placing calls and adding them to the queue. Once completed, a report will be downloaded from the DynamoDB table to the s3 iobucket.

### Stopping a  dialing job
To stop the dialing job gracefully, got to Systems Manager Parameter Store and change the parameter /connect/dialer/XXXX/activeDialer to False.

### Initiating a new dialing job
The dialing process marks each contact attempt on the dialing table as the way to keep track on the process, by the end of the dialing process all contacts on the table are marked as "attempted".Contacts need to be repopulated (by loading a new file or marking the specific contacts callAttempt parameter as False).

### About the inner workings.
1. The state machine will iterate over the dialing list, pulling contacts as agents become available. Bear in mind the Agent event stream processing function expects agents to become available before placing a new call. Also, it takes a couple of seconds once the agent sets its status to "Available" before the event is published.
2. The StepFunctions machine will invoke dialing workers based on the number of agents in Available State by the time the process starts. This dialing workers fetch contacts from the dialing list, place calls and wait for agents status changes to iterate over a new contact. There's a relationship of 1:1 of workers to the number of agents.
3. Once a dialing worker reaches the end of the list, the activeDialer paramter is set to false in the dialer configuration table. This stops all subsequent fetching attempt and finalized the dialing process. You can manually set the activeDialer attribute to false to stop the dialing process.

## Resource deletion
1. Remove any folders from the iobucket. You can browse to the S3 bucket (click on CloudFormation iobucket link on the resources tab for this stack), select all objects and click on delete.
2. Back on the cloudformation console, select the stack and click on Delete and confirm it by pressing Delete Stack. 
