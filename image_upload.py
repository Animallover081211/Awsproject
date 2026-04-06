"""
Task 2: Image Upload to S3 and SQS Trigger
Cloud Platform Development (CPD) Coursework

This script:
1. Uploads images from local folder to S3 bucket
2. Sends message to SQS queue after each upload
3. Runs continuously, uploading one image every 30 seconds

Author: Udukhomoh Francis
Student ID: S2230365
"""

import boto3
import os
import time
from pathlib import Path
from datetime import datetime
from config import STUDENT_ID, AWS_REGION, S3_BUCKET, SQS_QUEUE_URL, IMAGE_FOLDER, UPLOAD_INTERVAL


class ImageUploader:
    """Class to handle image upload to S3 and SQS messaging"""
    
    def __init__(self, bucket_name, queue_url, region='us-east-1'):
        """
        Initialize ImageUploader with S3 and SQS clients.
        
        Args:
            bucket_name: Name of the S3 bucket
            queue_url: URL of the SQS queue
            region: AWS region (default: us-east-1)
        """
        try:
            # Initialize S3 client
            self.s3_client = boto3.client('s3', region_name=region)
            # Initialize SQS client
            self.sqs_client = boto3.client('sqs', region_name=region)
            self.bucket_name = bucket_name
            self.queue_url = queue_url
            print(f"Initialized: S3 Bucket={bucket_name}, SQS Queue={queue_url}")
            
        except Exception as e:
            print(f"ERROR: Failed to initialize clients - {e}")
            raise
    
    def upload_image(self, image_path, s3_key=None):
        """
        Upload a single image file to S3 bucket.
        
        Args:
            image_path: Path to the local image file
            s3_key: Optional key name for S3 object (default: filename)
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        # Use filename as S3 key if not provided
        if s3_key is None:
            s3_key = os.path.basename(image_path)
        
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"ERROR: File not found - {image_path}")
                return False
            
            # Upload file to S3
            self.s3_client.upload_file(image_path, self.bucket_name, s3_key)
            print(f"SUCCESS: Uploaded {image_path} -> s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to upload {image_path} - {e}")
            return False
    
    def send_sqs_message(self, s3_key):
        """
        Send a message to SQS queue with image information.
        
        Args:
            s3_key: Name of the S3 object key
        
        Returns:
            str: Message ID if successful, None otherwise
        """
        # Create message body with image details
        message_body = {
            's3_bucket': self.bucket_name,
            's3_key': s3_key,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=str(message_body),
                MessageAttributes={
                    'image_name': {
                        'StringValue': s3_key,
                        'DataType': 'String'
                    }
                }
            )
            message_id = response['MessageId']
            print(f"SUCCESS: SQS message sent - {message_id}")
            return message_id
            
        except Exception as e:
            print(f"ERROR: Failed to send SQS message - {e}")
            return None
    
    def process_images(self, image_folder, interval=30):
        """
        Continuously upload images at specified intervals.
        
        Args:
            image_folder: Path to folder containing images
            interval: Time between uploads in seconds (default: 30)
        
        Returns:
            None (runs indefinitely until interrupted)
        """
        # Convert to Path object for easier handling
        image_folder = Path(image_folder)
        
        # Validate folder exists
        if not image_folder.exists():
            print(f"ERROR: Folder does not exist - {image_folder}")
            return
        
        # Define valid image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.jfif'}
        
        # Get list of image files
        image_files = [f for f in image_folder.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        if not image_files:
            print(f"WARNING: No image files found in {image_folder}")
            return
        
        print(f"\nFound {len(image_files)} images")
        print(f"Starting upload every {interval} seconds...")
        print("-" * 60)
        
        # Continuous upload loop
        while True:
            for image_file in image_files:
                # Upload image to S3
                upload_success = self.upload_image(str(image_file))
                
                # Send SQS message if upload successful
                if upload_success:
                    self.send_sqs_message(image_file.name)
                
                # Wait before next upload
                time.sleep(interval)
            
            print(f"\nCycle complete. Waiting {interval}s before next cycle...")
            time.sleep(interval)


def main():
    """
    Main function to run the image upload service.
    """
    try:
        print("=" * 60)
        print("TASK 2: IMAGE UPLOAD SERVICE")
        print("=" * 60)
        print(f"Configuration:")
        print(f"  S3 Bucket: {S3_BUCKET}")
        print(f"  SQS Queue: {SQS_QUEUE_URL}")
        print(f"  Image Folder: {IMAGE_FOLDER}")
        print(f"  Upload Interval: {UPLOAD_INTERVAL} seconds")
        print("-" * 60)
        
        # Create uploader instance
        uploader = ImageUploader(S3_BUCKET, SQS_QUEUE_URL, AWS_REGION)
        
        # Start processing images
        uploader.process_images(IMAGE_FOLDER, UPLOAD_INTERVAL)
        
    except KeyboardInterrupt:
        print("\n\nUpload service stopped by user")
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        exit(1)


if __name__ == '__main__':
    main()