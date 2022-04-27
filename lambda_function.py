from sms_spam_classifier_utilities import one_hot_encode
from sms_spam_classifier_utilities import vectorize_sequences
import boto3
import json
import numpy as np
import os 
import email
import re
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    
    # TRIGGER TEST
    print('lambda function triggered by s3')
    # print(event)

    vocabulary_length = 9013
    sagemaker = boto3.client('runtime.sagemaker')
    # replace with your own endpoint name
    ENDPOINT = os.environ['ENDPOINT_NAME']
    
    s3 = boto3.client('s3')
    
    # get object from s3
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        response = s3.get_object(Bucket=bucket, Key=key)
    except:
        print('Input type error')
        return
    
    try:
        message = response['Body'].read().decode()
        parser = email.message_from_string(message)
    except:
        print('email parser error')
        return
    
    parser = parser_convert(parser)
    
    # print(parser)
    # content encoding
    test_messages = [parser['body'].replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')]
    one_hot_test_messages = one_hot_encode(test_messages, vocabulary_length)
    encoded_test_messages = vectorize_sequences(one_hot_test_messages, vocabulary_length)
    
    payload = json.dumps(encoded_test_messages.tolist())
    response = sagemaker.invoke_endpoint(
                    EndpointName=ENDPOINT,
                    ContentType='application/json',
                    Body=payload
                )
               
    result = json.loads(response['Body'].read().decode())
    label = int(result['predicted_label'][0][0])
    score = result['predicted_probability'][0][0]
    
    send_SES(parser, label, score)
    # print(label, score)
    
    return 

def parser_convert(parser):
    '''
        decode the parser with json parser
        
        # param:
            parser: (message object) with full info of the email
        
        # return:
            content: (json) with required field in the email
            {
                'body': ...,
                'title': ...,
                'Date': ...,
                'sender': ...
            }
    '''
    
    # requirement = ['Subject', 'Date', 'Return-Path']
    content = {}
    
    # get the body of the email
    for val in parser.walk():
        if val.get_content_type() == 'text/plain':
        # plainText, htmlText = parser.get_payload()
            content['body'] = val.get_payload()
            break

    # get other info of the email
    for key, val in parser.items():
        if key == 'Subject':
            content['title'] = val
        elif key == 'Date':
            content[key] = re.split(',|-', val)[1].strip()
        elif key == 'Return-Path':
            content['sender'] = val[1:-1]
    
    return content

def send_SES(message, label, score):
    '''
        send reply email to the sender with spam result
        
        # param:
            message: (json) 
            email: (str)
            
        # return:
            None
    '''
    
    spam_type = {0: 'ham', 1: 'spam'}
    if label == 0:
        score = 1 - score
    
    score = ("%.3f" % (score * 100))
    # sender email address (has been verified)
    SENDER = 'artiste_yang@peteryoungy.com'
    
     # region location
    AWS_REGION = "us-east-1"
    
    # Create a new SES resource and specify a region.
    ses = boto3.client('ses', region_name=AWS_REGION)
    
    # emaildomain = client.list_verified_email_addresses()['VerifiedEmailAddresses']
    
    # #receiver email address (has been verified)
    RECIPIENT = message['sender']
    
    # The subject line for the email.
    title = message['title']
    
    # Email body for recipients with non-HTML email clients.
    BODY_TEXT = (
        '''We received your email sent at {} with the subject "{}".
Here is a {} character sample of the email body:
{} 
The email was categorized as {} with a {}% confidence.
        '''.format(message['Date'], message['title'], len(message['body']), message['body'].replace('\r', ''), spam_type[label], score) 
    )
                
    # HTML body of the email.
    BODY_HTML = """<html>
    <head> </head>
    <body>
      <h1>Spam Reply!</h1>
      <p> We received your email sent at {} with the subject <b>{}</b>. </p>
      <p> Here is a {} character sample of the email body: </p>
      <p> {} </p>
      <p> The email was categorized as <b>{}</b> with a <b>{}</b>% confidence. </p>
    </body>
    </html>
    """.format(message['Date'], message['title'], len(message['body']),
    message['body'].replace('\r\n\r\n', '</p> <br> <p>').replace('\r\n', '</p> <p>'), spam_type[label], score)           
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    SUBJECT = 'auto-reply'
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
    # Display an error if something goes wrong.	
    except ClientError as e: 
        print(e.response['Error']['Message'])
    else:
        print("Email sent!"),
        # print(response['MessageId'])