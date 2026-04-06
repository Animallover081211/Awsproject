import boto3
import json
import os

rekognition_client = boto3.client('rekognition')
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')

S3_BUCKET = os.environ.get('S3_BUCKET', 'your-bucket-name')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789012/ImageProcessingQueue')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

def detect_labels(bucket, key):
    """Detect labels in image using Rekognition"""
    response = rekognition_client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        MaxLabels=10,
        MinConfidence=70
    )
    
    labels = []
    for label in response['Labels']:
        labels.append({
            'Name': label['Name'],
            'Confidence': label['Confidence'],
            'Parents': [p['Name'] for p in label.get('Parents', [])]
        })
        
    return labels

def detect_faces(bucket, key):
    """Detect faces and emotions using Rekognition"""
    response = rekognition_client.detect_faces(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        Attributes=['ALL']
    )
    
    faces = []
    for face in response['FaceDetails']:
        emotions = []
        if 'Emotions' in face:
            for emotion in face['Emotions']:
                emotions.append({
                    'Type': emotion['Type'],
                    'Confidence': emotion['Confidence']
                })
                
        faces.append({
            'BoundingBox': face.get('BoundingBox'),
            'Confidence': face.get('Confidence'),
            'Emotions': emotions,
            'AgeRange': face.get('AgeRange'),
            'Gender': face.get('Gender'),
            'Smile': face.get('Smile'),
            'Eyeglasses': face.get('Eyeglasses'),
            'Sunglasses': face.get('Sunglasses')
        })
        
    return faces

def process_sqs_message():
    """Process SQS messages and trigger Rekognition"""
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
    
    try:
        message_body = json.loads(message['Body'])
        
        if 's3_bucket' in message_body:
            bucket = message_body['s3_bucket']
            key = message_body['s3_key']
        else:
            bucket = S3_BUCKET
            key = message_body.get('s3_key', message_body.get('image_name'))
            
        print(f"Processing image: s3://{bucket}/{key}")
        
        labels = detect_labels(bucket, key)
        faces = detect_faces(bucket, key)
        
        result = {
            'image_name': key,
            's3_bucket': bucket,
            's3_key': key,
            'labels': labels,
            'faces': faces,
            'timestamp': message_body.get('timestamp', '')
        }
        
        sqs_client.delete_message(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        
        print(f"Labels detected: {len(labels)}")
        print(f"Faces detected: {len(faces)}")
        
        return result
        
    except Exception as e:
        print(f"Error processing message: {e}")
        sqs_client.delete_message(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        return None

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    print("Lambda function triggered")
    print(f"Event: {json.dumps(event)}")
    
    result = process_sqs_message()
    
    if result:
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    else:
        return {
            'statusCode': 204,
            'body': 'No messages to process'
        }

def main():
    """Local testing function"""
    while True:
        result = process_sqs_message()
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No messages in queue")

if __name__ == '__main__':
    main()
