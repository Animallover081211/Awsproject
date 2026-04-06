import boto3
import time

def create_ec2_instance(ec2_client, key_name, security_group_id, subnet_id, instance_type='t2.micro'):
    """Create an EC2 instance"""
    response = ec2_client.run_instances(
        ImageId='ami-0c55b159cbfafe01f',
        InstanceType=instance_type,
        KeyName=key_name,
        MaxCount=1,
        MinCount=1,
        SecurityGroupIds=[security_group_id],
        SubnetId=subnet_id,
        UserData='''#!/bin/bash
                    apt-get update
                    apt-get install -y python3-pip
                    pip3 install boto3
                    '''
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"EC2 Instance created: {instance_id}")
    return instance_id

def wait_for_instance_running(ec2_client, instance_id):
    """Wait for EC2 instance to be in running state"""
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} is now running")

def describe_ec2_instance(ec2_client, instance_id):
    """Get EC2 instance details"""
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance = response['Reservations'][0]['Instances'][0]
    return {
        'InstanceId': instance['InstanceId'],
        'InstanceType': instance['InstanceType'],
        'ImageId': instance['ImageId'],
        'State': instance['State']['Name'],
        'PrivateIpAddress': instance.get('PrivateIpAddress'),
        'PublicIpAddress': instance.get('PublicIpAddress'),
        'SubnetId': instance.get('SubnetId'),
        'SecurityGroups': instance.get('SecurityGroups')
    }

def create_dynamodb_table(dynamodb_client, table_name, key_name='image_name'):
    """Create a DynamoDB table with single primary key"""
    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': key_name,
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': key_name,
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"DynamoDB Table '{table_name}' created")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"Table {table_name} is now active")
        return response
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists")
        return dynamodb_client.describe_table(TableName=table_name)

def main():
    aws_region = 'us-east-1'
    
    ec2_client = boto3.client('ec2', region_name=aws_region)
    dynamodb_client = boto3.client('dynamodb', region_name=aws_region)
    
    ec2_key_name = 'my-key-pair'
    security_group_id = 'sg-0123456789abcdef0'
    subnet_id = 'subnet-0123456789abcdef0'
    dynamodb_table_name = 'ImageMetadata'
    
    print("=== Creating EC2 Instance ===")
    instance_id = create_ec2_instance(ec2_client, ec2_key_name, security_group_id, subnet_id)
    wait_for_instance_running(ec2_client, instance_id)
    
    print("\n=== EC2 Instance Details ===")
    details = describe_ec2_instance(ec2_client, instance_id)
    for key, value in details.items():
        print(f"{key}: {value}")
    
    print("\n=== Creating DynamoDB Table ===")
    create_dynamodb_table(dynamodb_client, dynamodb_table_name, 'image_name')
    
    print("\n=== Task 1 Complete ===")

if __name__ == '__main__':
    main()
