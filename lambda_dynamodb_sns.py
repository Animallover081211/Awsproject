import boto3
import json
import os
from datetime import datetime

dynamodb_client = boto3.client('dynamodb')
sns_client = boto3.client('sns')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'ImageMetadata')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:ImageAlerts')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

TARGET_EMOTIONS = ['ANGRY', 'DISGUSTED']
CONFIDENCE_THRESHOLD = 80.0

def extract_rekognition_data(result):
    """Extract driving detection and emotions from Rekognition results"""
    image_name = result.get('image_name', '')
    
    is_driving = False
    driving_confidence = 0.0
    
    labels = result.get('labels', [])
    for label in labels:
        label_name = label.get('Name', '').lower()
        if 'driving' in label_name or 'car' in label_name or 'vehicle' in label_name or 'road' in label_name:
            is_driving = True
            driving_confidence = max(driving_confidence, label.get('Confidence', 0))
    
    emotions = []
    faces = result.get('faces', [])
    for face in faces:
        for emotion in face.get('Emotions', []):
            if emotion['Type'] in TARGET_EMOTIONS:
                emotions.append({
                    'Type': emotion['Type'],
                    'Confidence': emotion['Confidence']
                })
    
    return {
        'image_name': image_name,
        'is_driving': is_driving,
        'driving_confidence': driving_confidence,
        'emotions': emotions,
        'timestamp': result.get('timestamp', datetime.utcnow().isoformat())
    }

def store_in_dynamodb(data):
    """Store emotions data in DynamoDB"""
    if not data['emotions']:
        print(f"No target emotions found for {data['image_name']}")
        return False
    
    for emotion in data['emotions']:
        item = {
            'image_name': {'S': data['image_name']},
            'emotion': {'S': emotion['Type']},
            'emotion_confidence': {'N': str(emotion['Confidence'])},
            'is_driving': {'BOOL': data['is_driving']},
            'driving_confidence': {'N': str(data['driving_confidence'])},
            'timestamp': {'S': data['timestamp']}
        }
        
        try:
            dynamodb_client.put_item(TableName=DYNAMODB_TABLE, Item=item)
            print(f"Stored in DynamoDB: {data['image_name']} - {emotion['Type']}")
            return True
        except Exception as e:
            print(f"Error storing in DynamoDB: {e}")
            return False

def send_sns_notification(data):
    """Send email notification if conditions are met"""
    if not data['is_driving']:
        print("No driving detected - skipping notification")
        return False
    
    for emotion in data['emotions']:
        if emotion['Type'] == 'ANGRY' and emotion['Confidence'] > CONFIDENCE_THRESHOLD:
            message = (
                f"Alert: Driver Detected with High Anger\n\n"
                f"Image: {data['image_name']}\n"
                f"Emotion: {emotion['Type']}\n"
                f"Confidence: {emotion['Confidence']:.2f}%\n"
                f"Driving Detection: {data['driving_confidence']:.2f}%\n"
                f"Timestamp: {data['timestamp']}"
            )
            
            try:
                response = sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject='Alert: Dangerous Driving Detected',
                    Message=message
                )
                print(f"SNS Notification sent: {response['MessageId']}")
                return True
            except Exception as e:
                print(f"Error sending SNS notification: {e}")
                return False
    
    print("Conditions not met for notification")
    return False

def process_rekognition_result(result):
    """Process Rekognition results and trigger notifications"""
    data = extract_rekognition_data(result)
    
    print(f"Processing: {data['image_name']}")
    print(f"  Driving: {data['is_driving']} ({data['driving_confidence']:.2f}%)")
    print(f"  Emotions: {[e['Type'] for e in data['emotions']]}")
    
    stored = store_in_dynamodb(data)
    
    if stored:
        send_sns_notification(data)
    
    return {
        'stored': stored,
        'notification_sent': True
    }

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    print("Task 4 Lambda triggered")
    print(f"Event: {json.dumps(event)}")
    
    try:
        if 'rekognition_result' in event:
            result = event['rekognition_result']
        else:
            result = event.get('body', {})
            if isinstance(result, str):
                result = json.loads(result)
        
        response = process_rekognition_result(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def main():
    """Local testing"""
    test_result = {
        'image_name': 'test_image.jpg',
        'labels': [
            {'Name': 'Driving', 'Confidence': 95.0},
            {'Name': 'Car', 'Confidence': 90.0}
        ],
        'faces': [
            {
                'Emotions': [
                    {'Type': 'ANGRY', 'Confidence': 85.0},
                    {'Type': 'HAPPY', 'Confidence': 10.0}
                ]
            }
        ],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    process_rekognition_result(test_result)

if __name__ == '__main__':
    main()
