# AWS SpamDetection
Triggered when emails are sent to the email address under the domain we verified. Several things to notice:
1. Lambda function requires a numpy lambda `layer` to support the functions;
2. Model is trained by dataset from UCI SMS Spam Collection, for model details please refer to https://github.com/aws-samples/reinvent2018-srv404-lambda-sagemaker/tree/master/training;
3. When sending back email reply to the original sender, email content is retained, but image and superlink format are not able to be parsed.
4. For predict label, 0 represents ham and 1 represents spam.
