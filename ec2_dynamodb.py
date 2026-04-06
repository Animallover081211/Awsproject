"""
Task 1: Resource Creation - EC2 Instance and DynamoDB Table
Cloud Platform Development (CPD) Coursework

This script creates:
1. EC2 instance using Boto3
2. DynamoDB table with single primary key (image_name)

Author: Udukhomoh Francis
Student ID: S2230365
"""

import boto3
import time
from config import STUDENT_ID, AWS_REGION, DYNAMODB_TABLE, EC2_KEY_NAME, EC2_SECURITY_GROUP_ID, EC2_SUBNET_ID, EC2_INSTANCE_TYPE


def create_ec2_instance(ec2_client, key_name, security_group_id, subnet_id, instance_type='t2.micro'):
    """
    Create an EC2 instance using Boto3.
    
    Args:
        ec2_client: Boto3 EC2 client
        key_name: Name of the key pair for SSH access
        security_group_id: ID of the security group
        subnet_id: ID of the subnet
        instance_type: EC2 instance type (default: t2.micro)
    
    Returns:
        instance_id: ID of the created EC2 instance
    
    Raises:
        Exception: If instance creation fails
    """
    try:
        # AMI ID for Ubuntu 18.04 (update if needed for your region)
        ami_id = 'ami-0c55b159cbfafe01f'
        
        # User data script - installs Python and boto3 on EC2
        user_data = '''#!/bin/bash
                    apt-get update
                    apt-get install -y python3-pip
                    pip3 install boto3
                    '''
        
        response = ec2_client.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=key_name,
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[security_group_id],
            SubnetId=subnet_id,
            UserData=user_data
        )
        
        # Extract instance ID from response
        instance_id = response['Instances'][0]['InstanceId']
        print(f"EC2 Instance created successfully: {instance_id}")
        return instance_id
        
    except Exception as e:
        print(f"ERROR: Failed to create EC2 instance - {e}")
        raise


def wait_for_instance_running(ec2_client, instance_id):
    """
    Wait for EC2 instance to reach running state.
    
    Args:
        ec2_client: Boto3 EC2 client
        instance_id: ID of the EC2 instance
    
    Raises:
        Exception: If instance fails to start
    """
    try:
        # Create waiter for instance running state
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is now in running state")
        
    except Exception as e:
        print(f"ERROR: Instance did not start - {e}")
        raise


def describe_ec2_instance(ec2_client, instance_id):
    """
    Get detailed information about an EC2 instance.
    
    Args:
        ec2_client: Boto3 EC2 client
        instance_id: ID of the EC2 instance
    
    Returns:
        Dictionary containing instance details
    
    Raises:
        Exception: If describe instances fails
    """
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        
        # Extract instance details from first reservation
        instance = response['Reservations'][0]['Instances'][0]
        
        details = {
            'InstanceId': instance['InstanceId'],
            'InstanceType': instance['InstanceType'],
            'ImageId': instance['ImageId'],
            'State': instance['State']['Name'],
            'PrivateIpAddress': instance.get('PrivateIpAddress', 'N/A'),
            'PublicIpAddress': instance.get('PublicIpAddress', 'N/A'),
            'SubnetId': instance.get('SubnetId', 'N/A'),
            'SecurityGroups': instance.get('SecurityGroups', [])
        }
        
        return details
        
    except Exception as e:
        print(f"ERROR: Failed to describe instance - {e}")
        raise


def create_dynamodb_table(dynamodb_client, table_name, key_name='image_name'):
    """
    Create a DynamoDB table with single primary key.
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table to create
        key_name: Name of the primary key (default: image_name)
    
    Returns:
        Response from DynamoDB create_table or describe_table
    
    Raises:
        Exception: If table creation fails
    """
    try:
        # Create table with single partition key
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': key_name,
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': key_name,
                    'AttributeType': 'S'  # String type
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        print(f"DynamoDB Table '{table_name}' creation initiated")
        
        # Wait for table to become active
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"Table {table_name} is now active and ready to use")
        
        return response
        
    except dynamodb_client.exceptions.ResourceInUseException:
        # Table already exists, describe it
        print(f"Table {table_name} already exists")
        return dynamodb_client.describe_table(TableName=table_name)
        
    except Exception as e:
        print(f"ERROR: Failed to create DynamoDB table - {e}")
        raise


def main():
    """
    Main function to create EC2 instance and DynamoDB table.
    """
    try:
        # Initialize AWS clients
        ec2_client = boto3.client('ec2', region_name=AWS_REGION)
        dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        
        print("=" * 60)
        print("TASK 1: RESOURCE CREATION")
        print("=" * 60)
        
        # Create EC2 Instance
        print("\n--- Creating EC2 Instance ---")
        instance_id = create_ec2_instance(
            ec2_client, 
            EC2_KEY_NAME, 
            EC2_SECURITY_GROUP_ID, 
            EC2_SUBNET_ID,
            EC2_INSTANCE_TYPE
        )
        wait_for_instance_running(ec2_client, instance_id)
        
        # Get and display instance details
        print("\n--- EC2 Instance Details ---")
        details = describe_ec2_instance(ec2_client, instance_id)
        for key, value in details.items():
            print(f"  {key}: {value}")
        
        # Create DynamoDB Table
        print("\n--- Creating DynamoDB Table ---")
        create_dynamodb_table(dynamodb_client, DYNAMODB_TABLE, 'image_name')
        
        print("\n" + "=" * 60)
        print("TASK 1 COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        exit(1)


if __name__ == '__main__':
    main()