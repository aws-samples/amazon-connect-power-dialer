# Amazon Connect Power Dialer
This project contains source code and supporting files for a serverless dialer to be used on top of an Amazon Connect instance.

The basic operation of the solution is based on the principle of a Power Dialer: New calls are placed once agents complete previous calls. Since calls are placed automatically, the inefficiencies and error-prone nature of manual dialing are mitigated; yet, since calls are initiated until agents become available, you can maintain the warm nature of person to person contacts (no wait time for end users when being contacted).
The general workflow for this solution is as follows:

![Workflow](/images/DialerOnConnect-Workflow.jpg "Workflow")

1.	The administrator user loads a dialing list file using and initiates the dialing campaign.
2.	The dialer loads the configuration from Dialer Configuration table.
3.	The dialer pulls agent availability.
4.	The dialer pulls contacts from the Dialing list table based on agent concurrency for the first dialing batch. Each contact attempt is marked on the dialing list.
5.	Calls are launched in parallel based on the number of available agents.
6.	Successful call connections are put in queue so agents can answer immediately. 
7.	Agent and contact activity are monitored so calls are initiated once Agents wrap up the active calls.

This previous workflow maps to the simplified architecture shown below (AWS Lambda Functions and AWS Step Functions machines were not specified explicitly in sake of brevity). The solution leverages Amazon Connect API start outbound voice API to place calls, triggered by AWS Lambda Functions and orchestrated with Step Functions. Lambda Functions are also used to pull configuration, read contacts from the dialing list table and monitor Amazon Connect events on a Amazon Kinesis Stream (from both Contact Trace Records and Agent Events). Finally, Amazon DynamoDB and Amazon Simple Storage Service are used for dialing list, configuration parameters storage and input/output space for dialing lists and results. 
Roles for the Lambda Functions and Step Functions State Machines are defined in AWS Identity and Access Management to limit access to specific resources. 

![Architecture](/images/DialerOnConnect-Architecture.jpg "Architecture")

## Deployed resources

The project includes a cloud formation template with a Serverless Application Model (SAM) transform to deploy resources as follows:

### AWS Lambda functions

- initializeTable: Provides a one-off function to load the initial parameters for required tables.
- dial: Places calls using Amazon Connect boto3's start_outbound_voice_contact method.
- getAvailAgents: Gets agents available in the associated queue.
- getConfig: Gets the configuration parameters from a DynamoDB table.
- getContacts: Gets contact phone numbers to dial from a DynamoDB table.
- ListLoad: Loads dialing list from a CSV file to DynamoDB.
- ProcessAgentsEvents: Processes Agent Events to identify status changes and determine when would the next call should be placed.
- SaveResults: Generates a CSV file based from the dialing attempts.


### Step Functions

- DialerControlSF: Provides the general structure for the dialer. Pulls initial configuration and invokes parallel DialerThreadSF executions to perform the dialing process.
- DialerThreadSF: Provides a dialing thread execution that waits for agents to become available before placing calls.

### DynamoDB tables
- ActiveDialing: ContactIds to dialed contact relationship for contacts being dialed.
- DialerConfig: Parameters for the dialer opperation.
- dialList: Dialing list for the contacts.

### IAM roles
- ControlSFRole: Dialer Control Step Functions state Machine IAM role.
- ThreadSFRole: Dialer Thread Step Functions state Machine IAM role.
- PowerDialerLambdaRole: Lambda Functions IAM role.


## Prerequisites.
1. Amazon Connect Instance already set up.
2. AWS Console Access with administrator account.
3. Cloud9 IDE or AWS and SAM tools installed and properly configured with administrator credentials.

## Deploy the solution
1. Clone this repo.

`git clone https://github.com/aws-samples/amazon-connect-power-dialer`

2. Build the solution with SAM.

`sam build` 

if you get an error message about requirements you can try using containers.

`sam build -u` 


3. Deploy the solution.

`sam deploy -g`

SAM will ask for the name of the application (use "PowerDialer" or something similar) as all resources will be grouped under it; Region and a confirmation prompt before deploying resources, enter y.
SAM can save this information if you plan un doing changes, answer Y when prompted and accept the default environment and file name for the configuration.


## Configure Amazon Connect Agent Events and Contact Trace Records.

Agent activity is monitored using Agent Events, these events are pushed to a Kinesis Stream.

1. Browse to the Amazon Connect console.
2. Click on the instance alias name (Not on the Access URL).
3. Go to the Data Streaming section.
4. Verify the "Enable data streaming" checkbox is ticked or click it to enable streaming.
5. Under "Contact Trace Records" select Kinesis Stream.
6. Pick a Kinesis stream if you have set up one for this purpose or click on the "Create new Kinesis stream" to create one. If you're creating one, press the Create a Data Stream button on the Kinesis Console and assign a name ("AmazonConnectAgentEvents" for example) and a shard of 1 (you can update this value later) based on throughput.
6. Under Agent Events, pick the same Kinesis Stream. If you need different streams based on other applications, you can create 2 Kinesis streams and have them associated to each category of events. Later in the configuration, when you assign the trigger for the Agent Events Processing Lambda Function, make sure you set up both Kiinesis Streams as triggers.
7. Once the Kinesis Stream is set up, go back to Amazon Connect Console and select the recently created Stream, save the changes.


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

1. Navigate to the DynamoDB console and open the table named: "ConnectPD-DialerConfig".
2. Create entries for the following Items with the corresponding values. Note this items are case sensitive. The associated value must be specified with a "currentValue" attribute (also case sensitive).

| parameter   | currentValue |
|----------|:-------------:|
| connectid |  Connect instance ID |
| contactflow |contactflow ID|
| inputfile | Dialing list CSV file |
| io-bucket | Bucket where data will entered|
|queue|Id of the Connect queue to be used|
|table-activedialing|ConnectPD-ActiveDialing|
|table-dialerlist|ConnectPD-dialList|


## Set Triggers for Amazon Connect Agent Events

The agent activity is monitored thanks to the previously configured Kinesis Stream. This will be now configured as a trigger for a specific Lambda Function to process events.

1. Go to Applications and select "PowerDialer" or the name you specified when deploying the solution with SAM.
2. Click on ProcessAgentsEvents from the listed functions.
3. Click on triggers on the panel Function Overview.
4. On the Add trigger screen, click on the trigger list and select Kinesis.
5. Select the Kinesis stream you created previously.
6. Leave the rest of the parameters as specified by default. Click Add to save this trigger configuration.
 
## Operation
The solution relies on Step Functions as the main orchestation point and Lambda Functions as the processing units. Starting a campaign will include 2 steps:
1. Loading a dialing list.
2. Launching a dialing job.

### Loading a dialing list. 
To load a list, simply upload the CSV file (example is provided on file [sample-file](/sample-files/sample-load.csv "sample-file") ), point the dialer to this file and invoke the ListLoad function.

#### Uploading the file 
1. Generate a CSV file with the same structure as the example.
3. Go to cloudformation and select the stack created for this application (it will have the same name as you specified as application name).
4. Browse to the resources tab.
5. Click on the link for the iobucket name, a new window will open showing the bucket.
6. Click on the upload file and uplaod the file you created.

#### Configuring dialer
1. Navigate to the DynamoDB console and select the table named ConnectPD-DialerConfig.
2. Click on create item.
3. Specify the following parameter and currentValue. Pay attention as everything (key, attribute and value names) is case sensitive.

| parameter   | currentValue |
|----------|:-------------:|
| inputfile | CSV Filename with extension |

#### Invoking ListLoad Function
1. Navigate to the Lambda console.
2. Click on Applications and select "PowerDialer" or the name you used for the application.
3. Click on the ListLoad function name.
4. Click on the Test category. 
5. Now click on the Test button. This will initiate the load. The processing time will depend entirely on the number of entries on the list.

### Launching a dialing job.
The process to start the dialing job is through the Power Dialer Control Step Function, initiate an execution to launch the dialing job.

1. Navigate to the StepFunctions console.
2. Pick the Control Step Machine, it should have a name similar to: "DialerControlSF-XXXXXXXX".
3. Click Start Execution. A "Start Execution Window" will open, click Start Execution once again. This will start the dialing job, placing calls and adding them to the queue. Once completed, a report will be downloaded from the DynamoDB table to the s3 iobucket.

### Stopping a  dialing job
To stop the dialing job gracefully, got to the DialerConfig DynamoDB table and change the parameter ActiveDialer to false.


### Initiating a new dialing job
The dialing process marks each contact attempt on the dialing table as the way to keep track on the process, by the end of the dialing process all contacts on the table are marked as "attempted".
To reinitiate a dialing job to the same set of users, invoke the ListLoad Lambda function to reload the contacts with a reset state. 

### About the inner workings.
1. The state machine will iterate over the dialing list, pulling contacts as agents become available. Bear in mind the Agent event stream processing function expects agents to become available before placing a new call. Also, it takes a couple of seconds once the agent sets its status to "Available" before the event is published.
2. The StepFunctions machine will invoke dialing workers based on the number of agents in Available State by the time the process starts. This dialing workers fetch contacts from the dialing list, place calls and wait for agents status changes to iterate over a new contact. There's a relationship of 1:1 of workers to the number of agents.
3. Once a dialing worker reaches the end of the list, the activeDialer paramter is set to false in the dialer configuration table. This stops all subsequent fetching attempt and finalized the dialing process. You can manually set the activeDialer attribute to false to stop the dialing process.
4. 

## Resource deletion
1. Remove any folders from the iobucket. You can browse to the S3 bucket (click on CloudFormation iobucket link on the resources tab for this stack), select all objects and click on delete.
2. Back on the cloudformation console, select the stack and click on Delete and confirm it by pressing Delete Stack. 
