"""
Task 4: Lambda Function for DynamoDB Storage and SNS Notification
Cloud Platform Development (CPD) Coursework

This Lambda function:
1. Extracts data from Rekognition response (driving detection, emotions)
2. Stores ANGRY/DISGUSTED emotions in DynamoDB
3. Sends email notification if driving detected + angry + confidence > 80%

Author: Udukhomoh Francis
Student ID: S2230365
"""

import boto3
import json
import os
from datetime import datetime
from config import STUDENT_ID, AWS_REGION, DYNAMODB_TABLE, SNS_TOPIC_ARN


# Initialize AWS clients
dynamodb_client = boto3.client('dynamodb')
sns_client = boto3.client('sns')

# Get configuration from environment or config file
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', DYNAMODB_TABLE)
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', SNS_TOPIC_ARN)

# Configuration for emotion filtering and thresholds
TARGET_EMOTIONS = ['ANGRY', 'DISGUSTED']
CONFIDENCE_THRESHOLD = 80.0


def extract_rekognition_data(result):
    """
    Extract driving detection and emotions from Rekognition results.
    
    Analyzes labels to detect if person is driving (looks for driving,
    car, vehicle, road keywords). Extracts emotions from face detection.
    
    Args:
        result: Dictionary containing Rekognition detection results
    
    Returns:
        dict: Extracted data including driving status and emotions
    """
    image_name = result.get('image_name', '')
    
    # Initialize driving detection
    is_driving = False
    driving_confidence = 0.0
    
    # Check labels for driving-related keywords
    labels = result.get('labels', [])
    driving_keywords = ['driving', 'car', 'vehicle', 'road', 'traffic', 'automobile']
    
    for label in labels:
        label_name = label.get('Name', '').lower()
        # Check if any driving keyword is in the label
        if any(keyword in label_name for keyword in driving_keywords):
            is_driving = True
            # Keep highest confidence
            driving_confidence = max(driving_confidence, label.get('Confidence', 0))
    
    # Extract target emotions (ANGRY and DISGUSTED) from faces
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
    """
    Store emotion data in DynamoDB table.
    
    Only stores ANGRY and DISGUSTED emotions with confidence values.
    
    Args:
        data: Dictionary containing extracted emotion data
    
    Returns:
        bool: True if storage successful, False otherwise
    """
    if not data['emotions']:
        print(f"INFO: No target emotions (ANGRY/DISGUSTED) found for {data['image_name']}")
        return False
    
    # Store each emotion as a separate item
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
            print(f"SUCCESS: Stored in DynamoDB - {data['image_name']} | {emotion['Type']} | {emotion['Confidence']}%")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to store in DynamoDB - {e}")
            return False


def send_sns_notification(data):
    """
    Send email notification via SNS if conditions are met.
    
    Sends notification ONLY if:
    - Driving is detected (is_driving = True)
    - Emotion is ANGRY
    - Confidence > 80%
    
    Args:
        data: Dictionary containing extracted emotion and driving data
    
    Returns:
        bool: True if notification sent, False otherwise
    """
    # Check if driving is detected
    if not data['is_driving']:
        print("INFO: No driving detected - skipping notification")
        return False
    
    # Check if any emotion meets the criteria
    for emotion in data['emotions']:
        if emotion['Type'] == 'ANGRY' and emotion['Confidence'] > CONFIDENCE_THRESHOLD:
            # Build notification message
            message = (
                f"ALERT: Dangerous Driving Detected\n\n"
                f"Image: {data['image_name']}\n"
                f"Emotion: {emotion['Type']}\n"
                f"Confidence: {emotion['Confidence']:.2f}%\n"
                f"Driving Detection: {data['driving_confidence']:.2f}%\n"
                f"Timestamp: {data['timestamp']}\n\n"
                f"Please take appropriate action."
            )
            
            try:
                response = sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject='ALERT: Dangerous Driving Detected',
                    Message=message
                )
                message_id = response['MessageId']
                print(f"SUCCESS: SNS notification sent - MessageID: {message_id}")
                return True
                
            except Exception as e:
                print(f"ERROR: Failed to send SNS notification - {e}")
                return False
    
    print("INFO: Conditions not met for notification (not angry or confidence < 80%)")
    return False


def process_rekognition_result(result):
    """
    Process Rekognition results - extract data, store in DB, send notification.
    
    This is the main processing function that coordinates all steps.
    
    Args:
        result: Dictionary containing Rekognition detection results
    
    Returns:
        dict: Processing result with storage and notification status
    """
    print("-" * 40)
    print(f"Processing: {result.get('image_name', 'unknown')}")
    
    # Step 1: Extract data from Rekognition response
    data = extract_rekognition_data(result)
    
    print(f"  Driving: {data['is_driving']} ({data['driving_confidence']:.1f}%)")
    print(f"  Emotions: {[e['Type'] for e in data['emotions']]}")
    
    # Step 2: Store in DynamoDB
    stored = store_in_dynamodb(data)
    
    # Step 3: Send notification if stored
    if stored:
        notification_sent = send_sns_notification(data)
    else:
        notification_sent = False
    
    return {
        'stored': stored,
        'notification_sent': notification_sent
    }


def lambda_handler(event, context):
    """
    AWS Lambda handler function - entry point for Lambda execution.
    
    This function is triggered by DynamoDB stream or direct invocation.
    
    Args:
        event: Lambda event data (DynamoDB stream or API Gateway)
        context: Lambda context object
    
    Returns:
        dict: HTTP response with status code and body
    """
    print("=" * 60)
    print("Lambda Function: Task 4 - DynamoDB Storage & SNS")
    print("=" * 60)
    
    try:
        # Handle different event types
        if 'rekognition_result' in event:
            # Direct invocation with result data
            result = event['rekognition_result']
        else:
            # Parse from event body
            result = event.get('body', {})
            if isinstance(result, str):
                result = json.loads(result)
        
        # Process the result
        response = process_rekognition_result(result)
        
        print(f"Result: {response}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def main():
    """
    Main function for local testing.
    Tests with sample Rekognition result.
    """
    print("=" * 60)
    print("Local Testing Mode")
    print("=" * 60)
    
    # Sample test data
    test_result = {
        'image_name': 'test_image.jpg',
        'labels': [
            {'Name': 'Driving', 'Confidence': 95.0},
            {'Name': 'Car', 'Confidence': 90.0},
            {'Name': 'Road', 'Confidence': 85.0}
        ],
        'faces': [
            {
                'Emotions': [
                    {'Type': 'ANGRY', 'Confidence': 85.0},
                    {'Type': 'DISGUSTED', 'Confidence': 20.0},
                    {'Type': 'HAPPY', 'Confidence': 10.0}
                ]
            }
        ],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Process test data
    result = process_rekognition_result(test_result)
    
    print("\n--- Test Result ---")
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()