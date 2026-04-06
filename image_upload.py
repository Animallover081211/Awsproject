import boto3
import os
import time
from pathlib import Path
from datetime import datetime

class ImageUploader:
    def __init__(self, bucket_name, queue_url, region='us-east-1'):
        self.s3_client = boto3.client('s3', region_name=region)
        self.sqs_client = boto3.client('sqs', region_name=region)
        self.bucket_name = bucket_name
        self.queue_url = queue_url
        
    def upload_image(self, image_path, s3_key=None):
        """Upload image to S3"""
        if s3_key is None:
            s3_key = os.path.basename(image_path)
            
        try:
            self.s3_client.upload_file(image_path, self.bucket_name, s3_key)
            print(f"Uploaded: {image_path} -> s3://{self.bucket_name}/{s3_key}")
            return True
        except Exception as e:
            print(f"Error uploading {image_path}: {e}")
            return False
            
    def send_sqs_message(self, s3_key):
        """Send message to SQS with image info"""
        message_body = {
            's3_bucket': self.bucket_name,
            's3_key': s3_key,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
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
            print(f"SQS Message sent: {response['MessageId']}")
            return response['MessageId']
        except Exception as e:
            print(f"Error sending SQS message: {e}")
            return None
            
    def process_images(self, image_folder, interval=30):
        """Upload images every interval seconds"""
        image_folder = Path(image_folder)
        
        if not image_folder.exists():
            print(f"Error: Folder {image_folder} does not exist")
            return
            
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        image_files = [f for f in image_folder.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        if not image_files:
            print(f"No image files found in {image_folder}")
            return
            
        print(f"Found {len(image_files)} images. Starting upload every {interval} seconds...")
        print("-" * 60)
        
        while True:
            for image_file in image_files:
                self.upload_image(str(image_file))
                self.send_sqs_message(image_file.name)
                time.sleep(interval)
                
            print(f"Cycle complete. Waiting {interval}s before next cycle...")
            time.sleep(interval)

def main():
    BUCKET_NAME = 'your-bucket-name'
    QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/ImageProcessingQueue'
    IMAGE_FOLDER = '/path/to/images'
    INTERVAL = 30
    
    uploader = ImageUploader(BUCKET_NAME, QUEUE_URL)
    
    print("=== EC2 Image Upload Service ===")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Queue: {QUEUE_URL}")
    print(f"Image Folder: {IMAGE_FOLDER}")
    print(f"Upload Interval: {INTERVAL} seconds")
    print("-" * 60)
    
    try:
        uploader.process_images(IMAGE_FOLDER, INTERVAL)
    except KeyboardInterrupt:
        print("\nUpload service stopped")

if __name__ == '__main__':
    main()
