# AWS Image Processing Pipeline

Cloud Platform Development (CPD) Coursework - Label & Face Detection

## Overview
Automated image processing system that detects driving scenarios and facial emotions using AWS services.

## Architecture
```
EC2 → S3 → SQS → Lambda → Rekognition → DynamoDB → SNS → Email
```

## Files

| File | Description |
|------|-------------|
| `config.py` | Configuration - update with your AWS credentials and Student ID |
| `ec2_dynamodb.py` | Task 1: Creates EC2 instance and DynamoDB table |
| `image_upload.py` | Task 2: Uploads images to S3 every 30 seconds |
| `lambda_rekognition.py` | Task 3: Lambda function for label/face detection |
| `lambda_dynamodb_sns.py` | Task 4: Lambda for DynamoDB storage + SNS email |
| `cloudformation_sqs_s3.yaml` | Task 1: CloudFormation for SQS and S3 |
| `cloudformation_sns.yaml` | Task 3: CloudFormation for SNS topic |

## Setup

1. Update `config.py` with your:
   - Student ID (S2230365)
   - AWS credentials
   - EC2 key pair, security group, subnet

2. Deploy CloudFormation stacks:
   - `cloudformation_sqs_s3.yaml`
   - `cloudformation_sns.yaml`

3. Create Lambda functions and add environment variables

4. Run `ec2_dynamodb.py` to create EC2 and DynamoDB

## Requirements
- Python 3
- boto3 (`pip install boto3`)
- AWS Academy Learner Lab access