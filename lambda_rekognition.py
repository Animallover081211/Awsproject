"""
Task 3: Lambda Function for Label and Face Detection
Cloud Platform Development (CPD) Coursework

This Lambda function:
1. Reads messages from SQS queue
2. Invokes AWS Rekognition for label detection
3. Invokes AWS Rekognition for face detection
4. Returns results for further processing

Author: Udukhomoh Francis
Student ID: S2230365
"""

import boto3
import json
import os
from config import STUDENT_ID, AWS_REGION, S3_BUCKET, SQS_QUEUE_URL


# Initialize AWS clients
rekognition_client = boto3.client('rekognition')
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')

# Get configuration from environment or config file
S3_BUCKET = os.environ.get('S3_BUCKET', S3_BUCKET)
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', SQS_QUEUE_URL)


def detect_labels(bucket, key):
    """
    Detect labels in an image using AWS Rekognition.
    
    Args:
        bucket: Name of the S3 bucket
        key: Key name of the S3 object
    
    Returns:
        list: List of detected labels with name and confidence
    
    Raises:
        Exception: If label detection fails
    """
    try:
        response = rekognition_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10,
            MinConfidence=70  # Only return labels with 70%+ confidence
        )
        
        labels = []
        for label in response['Labels']:
            labels.append({
                'Name': label['Name'],
                'Confidence': label['Confidence'],
                'Parents': [p['Name'] for p in label.get('Parents', [])]
            })
        
        print(f"Detected {len(labels)} labels")
        return labels
        
    except Exception as e:
        print(f"ERROR: Label detection failed - {e}")
        raise


def detect_faces(bucket, key):
    """
    Detect faces and emotions in an image using AWS Rekognition.
    
    Args:
        bucket: Name of the S3 bucket
        key: Key name of the S3 object
    
    Returns:
        list: List of detected faces with details including emotions
    
    Raises:
        Exception: If face detection fails
    """
    try:
        response = rekognition_client.detect_faces(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            Attributes=['ALL']  # Get all face attributes including emotions
        )
        
        faces = []
        for face in response['FaceDetails']:
            # Extract emotions
            emotions = []
            if 'Emotions' in face:
                for emotion in face['Emotions']:
                    emotions.append({
                        'Type': emotion['Type'],
                        'Confidence': emotion['Confidence']
                    })
            
            # Build face details dictionary
            face_details = {
                'BoundingBox': face.get('BoundingBox'),
                'Confidence': face.get('Confidence'),
                'Emotions': emotions,
                'AgeRange': face.get('AgeRange'),
                'Gender': face.get('Gender'),
                'Smile': face.get('Smile'),
                'Eyeglasses': face.get('Eyeglasses'),
                'Sunglasses': face.get('Sunglasses')
            }
            faces.append(face_details)
        
        print(f"Detected {len(faces)} faces")
        return faces
        
    except Exception as e:
        print(f"ERROR: Face detection failed - {e}")
        raise


def process_sqs_message():
    """
    Process a single message from the SQS queue.
    
    Reads message, retrieves image from S3, performs Rekognition
    detection, and deletes message from queue.
    
    Returns:
        dict: Results containing image name, labels, and faces, or None if no message
    """
    try:
        # Receive message from SQS
        response = sqs_client.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            MessageAttributeNames=['image_name'],
            AttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        if not messages:
            return None
        
        message = messages[0]
        receipt_handle = message['ReceiptHandle']
        
        # Parse message body
        try:
            message_body = json.loads(message['Body'])
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in message body")
            sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
            return None
        
        # Extract bucket and key from message
        if 's3_bucket' in message_body:
            bucket = message_body['s3_bucket']
            key = message_body['s3_key']
        else:
            # Use default bucket if not in message
            bucket = S3_BUCKET
            key = message_body.get('s3_key', message_body.get('image_name'))
        
        print(f"Processing image: s3://{bucket}/{key}")
        
        # Perform label detection
        labels = detect_labels(bucket, key)
        
        # Perform face detection
        faces = detect_faces(bucket, key)
        
        # Build result dictionary
        result = {
            'image_name': key,
            's3_bucket': bucket,
            's3_key': key,
            'labels': labels,
            'faces': faces,
            'timestamp': message_body.get('timestamp', '')
        }
        
        # Delete message from queue after successful processing
        sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        print(f"Message deleted: {receipt_handle}")
        
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to process SQS message - {e}")
        # Attempt to delete message to prevent reprocessing
        try:
            sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        except:
            pass
        return None


def lambda_handler(event, context):
    """
    AWS Lambda handler function - entry point for Lambda execution.
    
    This function is called when Lambda is triggered (e.g., by SQS event).
    
    Args:
        event: Lambda event data (can be SQS event or direct invocation)
        context: Lambda context object
    
    Returns:
        dict: HTTP response with status code and body
    """
    print("=" * 60)
    print("Lambda Function: Task 3 - Rekognition Detection")
    print("=" * 60)
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Process SQS message
        result = process_sqs_message()
        
        if result:
            print(f"SUCCESS: Processed {result['image_name']}")
            print(f"  Labels: {len(result['labels'])}")
            print(f"  Faces: {len(result['faces'])}")
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        else:
            print("No messages to process")
            return {
                'statusCode': 204,
                'body': 'No messages to process'
            }
            
    except Exception as e:
        print(f"ERROR: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def main():
    """
    Main function for local testing (not used in Lambda).
    Runs continuous polling for SQS messages.
    """
    print("=" * 60)
    print("Local Testing Mode - SQS Polling")
    print("=" * 60)
    
    while True:
        result = process_sqs_message()
        if result:
            print("\n--- Result ---")
            print(json.dumps(result, indent=2))
        else:
            print("No messages in queue, waiting...")


if __name__ == '__main__':
    main()