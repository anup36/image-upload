import boto3
from botocore.exceptions import ClientError
from config import Config
import logging

logger = logging.getLogger(__name__)

class AWSServices:
    """AWS Services Manager for S3 and DynamoDB operations"""
    
    def __init__(self):
        self.s3_client = None
        self.dynamodb = None
        self.dynamodb_table = None
        self.lambda_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AWS service clients"""
        try:
            # S3 Client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            
            # DynamoDB Resource
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            self.dynamodb_table = self.dynamodb.Table(Config.DYNAMODB_TABLE_NAME)
            
            # Lambda Client
            self.lambda_client = boto3.client(
                'lambda',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            
            logger.info("AWS clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
    
    # S3 Operations
    def upload_to_s3(self, file_obj, file_name, content_type):
        """Upload file to S3 bucket"""
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                Config.S3_BUCKET_NAME,
                file_name,
                ExtraArgs={'ContentType': content_type}
            )
            return True
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    def get_s3_url(self, file_name):
        """Generate pre-signed URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': Config.S3_BUCKET_NAME, 'Key': file_name},
                ExpiresIn=3600  # URL valid for 1 hour
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate S3 URL: {e}")
            return None
    
    def download_from_s3(self, file_name):
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=Config.S3_BUCKET_NAME,
                Key=file_name
            )
            return response['Body'].read(), response['ContentType']
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return None, None
    
    def delete_from_s3(self, file_name):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=Config.S3_BUCKET_NAME,
                Key=file_name
            )
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False
    
    # DynamoDB Operations
    def put_item(self, item):
        """Put item in DynamoDB table"""
        try:
            self.dynamodb_table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB put_item failed: {e}")
            return False
    
    def get_item(self, image_id):
        """Get item from DynamoDB table"""
        try:
            response = self.dynamodb_table.get_item(Key={'id': image_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"DynamoDB get_item failed: {e}")
            return None
    
    def scan_items(self, filter_expression=None, expression_values=None):
        """Scan DynamoDB table with optional filter"""
        try:
            if filter_expression and expression_values:
                response = self.dynamodb_table.scan(
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_values
                )
            else:
                response = self.dynamodb_table.scan()
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"DynamoDB scan failed: {e}")
            return []
    
    def delete_item(self, image_id):
        """Delete item from DynamoDB table"""
        try:
            self.dynamodb_table.delete_item(Key={'id': image_id})
            return True
        except ClientError as e:
            logger.error(f"DynamoDB delete_item failed: {e}")
            return False
    
    # Lambda Operations
    def invoke_lambda(self, function_name, payload):
        """Invoke Lambda function"""
        try:
            import json
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            result = json.loads(response['Payload'].read())
            return result
        except ClientError as e:
            logger.error(f"Lambda invocation failed: {e}")
            return None

# Global instance
aws_services = AWSServices()