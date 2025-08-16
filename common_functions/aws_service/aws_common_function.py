import os
import sys
import time
import boto3
from botocore.exceptions import ClientError
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common_functions.utils.logging_config import logger

qa_aws_access_key_id = (os.getenv("DEV_ACCOUNT_AWS_ACCESS_KEY_ID"))
qa_aws_secret_access_key = (os.getenv("DEV_ACCOUNT_AWS_SECRET_ACCESS_KEY"))
qa_region_name = (os.getenv("DEV_ACCOUNT_AWS_REGION"))

class aws_clien_manager:
    
    # Dictionary to store active clients
    clients = {}

    @classmethod
    def create_session(cls, aws_access_key_id=qa_aws_access_key_id, aws_secret_access_key=qa_aws_secret_access_key, region_name=qa_region_name):
        """
        Create a new Boto3 session.
        """
        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

    @classmethod
    def activate_s3_client(cls, session):
        """
        Activate and return an S3 client.
        """
        if 's3' not in cls.clients:
            cls.clients['s3'] = session.client('s3')
        return cls.clients['s3']

    @classmethod
    def activate_athena_client(cls, session):
        """
        Activate and return an Athena client.
        """
        if 'athena' not in cls.clients:
            cls.clients['athena'] = session.client('athena')
        return cls.clients['athena']

    @classmethod
    def activate_dynamodb_client(cls, session):
        """
        Activate and return a DynamoDB client.
        """
        if 'dynamodb' not in cls.clients:
            cls.clients['dynamodb'] = session.client('dynamodb')
        return cls.clients['dynamodb']

    @classmethod
    def close_all_clients(cls):
        """
        Close all active clients.
        """
        for service_name, client in cls.clients.items():
            try:
                client.close()
                logger.info(f"Closed {service_name} client.")
            except AttributeError:
                logger.info(f"{service_name} client does not support explicit closure.")
        cls.clients.clear()


    # ## Usage example: ###
    # # Create a session (use default credentials or provide your own)
    # session = aws_clien_manager.create_session()

    # # Activate and use the S3 client
    # s3_client = aws_clien_manager.activate_s3_client(session)
    # print(s3_client.list_buckets())

    # # Activate and use the Athena client
    # athena_client = aws_clien_manager.activate_athena_client(session)
    # # print(athena_client.list_query_executions())

    # # Activate and use the DynamoDB client
    # dynamodb_client = aws_clien_manager.activate_dynamodb_client(session)


    # # print(dynamodb_client.list_tables())

    # # Close all clients
    # aws_clien_manager.close_all_clients()

    # print("Hi")

class s3_operations_manager:
    # Dictionary to store active operations
    operations = {}

    @classmethod
    def upload_file(cls, s3_client, file_path, bucket, s3_key):
        """
        Upload a file to S3 bucket
        :param s3_client: Active S3 client
        :param file_path: Local path of the file
        :param bucket: S3 bucket name
        :param s3_key: S3 object key (path in bucket)
        """
        try:
            s3_client.upload_file(file_path, bucket, s3_key)
            logger.info(f"Successfully uploaded {file_path} to {bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.info(f"Error uploading file: {e}")
            return False

    @classmethod
    def download_file(cls, s3_client, bucket, s3_key, local_path):
        """
        Download a file from S3 bucket
        :param s3_client: Active S3 client
        :param bucket: S3 bucket name
        :param s3_key: S3 object key (path in bucket)
        :param local_path: Local path to save the file
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3_client.download_file(bucket, s3_key, local_path)
            logger.info(f" \n Successfully downloaded {bucket}/{s3_key} to {local_path}")
            return True
        except ClientError as e:
            logger.info(f"Error downloading file: {e}")
            return False

    @classmethod
    def read_file_content(cls, s3_client, bucket, s3_key):
        """
        Read content of a file from S3 bucket
        :param s3_client: Active S3 client
        :param bucket: S3 bucket name
        :param s3_key: S3 object key (path in bucket)
        :return: File content as string
        """
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            logger.info(f"Error reading file: {e}")
            return None

    @classmethod
    def list_files(cls, s3_client, bucket, prefix=''):
        """
        List files in S3 bucket with given prefix
        :param s3_client: Active S3 client
        :param bucket: S3 bucket name
        :param prefix: Prefix to filter files
        :return: List of file keys
        """
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            logger.info(f"Error listing files: {e}")
            return []
        
    @classmethod
    def generate_presigned_url(cls, s3_client, bucket, s3_key, expiration=3600):
        """
        Generate a presigned URL for a given S3 object
        """
        try:
            response = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.info(f"Error generating presigned URL: {e}")
            return None
        
    @classmethod
    def s3_file_exists_checker(cls, s3_client, bucket, s3_key):
        """
        Check if a file exists in S3 bucket
        """
        try:
            s3_client.head_object(Bucket=bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False


    ### Usage example: ###
    # # Create session and get S3 client
    # session = aws_clien_manager.create_session()
    # s3_client = aws_clien_manager.activate_s3_client(session)

    # # Use S3 operations
    # s3_operations_manager.upload_file(s3_client, 'local_file.txt', 'my-bucket', 'path/in/s3/file.txt')
    # s3_operations_manager.download_file(s3_client, 'my-bucket', 'path/in/s3/file.txt', 'downloaded_file.txt')
    # content = s3_operations_manager.read_file_content(s3_client, 'my-bucket', 'path/in/s3/file.txt')
    # files = s3_operations_manager.list_files(s3_client, 'my-bucket', 'path/in/s3/')

class athena_operations_manager:
    # Dictionary to store active operations
    operations = {}

    @classmethod
    def execute_query(cls, athena_client, query, database, s3_output):
        """
        Execute query in Amazon Athena
        :param athena_client: Active Athena client
        :param query: SQL query to execute
        :param database: Database name
        :param s3_output: S3 location for query results
        :return: Query execution ID
        """
        try:
            response = athena_client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database},
                ResultConfiguration={'OutputLocation': s3_output}
            )
            return response['QueryExecutionId']
        except ClientError as e:
            logger.info(f"Error executing query: {e}")
            return None

    @classmethod
    def check_query_status(cls, athena_client, query_execution_id):
        """
        Check the status of the query execution
        :param athena_client: Active Athena client
        :param query_execution_id: ID of the query execution
        :return: Query status
        """
        try:
            response = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            return response['QueryExecution']['Status']['State']
        except ClientError as e:
            logger.info(f"Error checking query status: {e}")
            return None

    @classmethod
    def get_query_results(cls, athena_client, query_execution_id):
        """
        Get results of a completed query
        :param athena_client: Active Athena client
        :param query_execution_id: ID of the query execution
        :return: Query results
        """
        try:
            response = athena_client.get_query_results(QueryExecutionId=query_execution_id)
            return response['ResultSet']
        except ClientError as e:
            logger.info(f"Error getting query results: {e}")
            return None

    @classmethod
    def wait_for_query_completion(cls, athena_client, query_execution_id, check_interval=2):
        """
        Wait for query to complete
        :param athena_client: Active Athena client
        :param query_execution_id: ID of the query execution
        :param check_interval: Time between status checks in seconds
        :return: Final query status
        """
        while True:
            status = cls.check_query_status(athena_client, query_execution_id)
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                return status
            logger.info("Athena Query is still running...")
            time.sleep(check_interval)

    @classmethod
    def format_query_results(cls, results):
        """
        Format query results into a readable format
        :param results: Query results from get_query_results
        :return: Formatted results as list of dictionaries
        """
        if not results or 'Rows' not in results:
            return []

        # Get column names from first row
        columns = [col.get('VarCharValue', '') for col in results['Rows'][0]['Data']]
        
        # Format data rows
        formatted_results = []
        for row in results['Rows'][1:]:  # Skip header row
            row_data = {}
            for i, col in enumerate(row['Data']):
                value = col.get('VarCharValue', None)
                row_data[columns[i]] = value
            formatted_results.append(row_data)
        
        return formatted_results


    ## Usage example: ###
    # Create session and get Athena client
    # session = aws_clien_manager.create_session()
    # athena_client = aws_clien_manager.activate_athena_client(session)

    # # Execute query
    # query = "SELECT * FROM your_table LIMIT 10"
    # database = "your_database"
    # s3_output = "s3://your-bucket/query-results/"


    # today_date = datetime.now().strftime('%d-%m-%Y')

    # # Execute query
    # query = 'SELECT * FROM "fb_shipper_staging"."fb_offers_response" limit 10;'
    # database = "fb_shipper_staging"
    # s3_output = f's3://aws-athena-query-results-454782328663-ap-south-1/qa_test_automation/test_script_query_results/{today_date}/'

    # query_id = athena_operations_manager.execute_query(athena_client, query, database, s3_output)

    # # Wait for completion
    # status = athena_operations_manager.wait_for_query_completion(athena_client, query_id)

    # if status == 'SUCCEEDED':
    #     # Get and format results
    #     results = athena_operations_manager.get_query_results(athena_client, query_id)
    #     formatted_results = athena_operations_manager.format_query_results(results)
    #     logger.info(formatted_results)


    # # Close all clients
    # aws_clien_manager.close_all_clients()

    # logger.info("Hi")

class dynamodb_operations_manager:
    # Dictionary to store active operations
    operations = {}

    @classmethod
    def get_item(cls, dynamodb_client, table_name, key):
        """
        Get an item from DynamoDB table
        :param dynamodb_client: Active DynamoDB client
        :param table_name: Name of the DynamoDB table
        :param key: Dictionary containing the primary key attributes
        :return: Item if found, None otherwise
        """
        try:
            response = dynamodb_client.get_item(
                TableName=table_name,
                Key=key
            )
            return response.get('Item')
        except ClientError as e:
            logger.info(f"Error getting item: {e}")
            return None

    @classmethod
    def put_item(cls, dynamodb_client, table_name, item):
        """
        Put an item into DynamoDB table
        :param dynamodb_client: Active DynamoDB client
        :param table_name: Name of the DynamoDB table
        :param item: Dictionary containing the item attributes
        :return: True if successful, False otherwise
        """
        try:
            dynamodb_client.put_item(
                TableName=table_name,
                Item=item
            )
            logger.info(f"Successfully put item in {table_name}")
            return True
        except ClientError as e:
            logger.info(f"Error putting item: {e}")
            return False



    @classmethod
    def query_table(cls, dynamodb_client, table_name, key_condition_expression, expression_attribute_values=None, filter_expression=None):
        """
        Query items from DynamoDB table
        :param dynamodb_client: Active DynamoDB client
        :param table_name: Name of the DynamoDB table
        :param key_condition_expression: Expression defining the query conditions
        :param expression_attribute_values: Dictionary of values used in key condition expression
        :param filter_expression: Optional filter expression for additional filtering
        :return: List of items matching the query
        """
        try:
            params = {
                'TableName': table_name,
                'KeyConditionExpression': key_condition_expression
            }
            if expression_attribute_values:
                params['ExpressionAttributeValues'] = expression_attribute_values
            if filter_expression:
                params['FilterExpression'] = filter_expression

            response = dynamodb_client.query(**params)
            return response.get('Items', [])
        except ClientError as e:
            logger.info(f"Error querying table: {e}")
            return []

    @classmethod
    def scan_table(cls, dynamodb_client, table_name, filter_expression=None, expression_attribute_values=None, limit=None):
        """
        Scan items from DynamoDB table
        :param dynamodb_client: Active DynamoDB client
        :param table_name: Name of the DynamoDB table
        :param filter_expression: Expression defining the scan filter
        :param expression_attribute_values: Dictionary of values used in filter expression
        :param limit: Maximum number of items to return
        :return: List of items matching the scan
        """
        try:
            params = {
                'TableName': table_name
            }
            if filter_expression:
                params['FilterExpression'] = filter_expression
            if expression_attribute_values:
                params['ExpressionAttributeValues'] = expression_attribute_values
            if limit:
                params['Limit'] = limit

            response = dynamodb_client.scan(**params)
            return response.get('Items', [])
        except ClientError as e:
            logger.info(f"Error scanning table: {e}")
            return []

    @classmethod
    def query_results_to_df(cls, items):
        """
        Convert DynamoDB query/scan results to pandas DataFrame
        :param items: List of items from DynamoDB query/scan
        :return: pandas DataFrame containing the query results
        """
        try:
            # Convert DynamoDB items to regular dictionaries
            converted_items = []
            for item in items:
                converted_item = {}
                for key, value in item.items():
                    # Extract the value from DynamoDB's type format
                    if 'S' in value:  # String
                        converted_item[key] = value['S']
                    elif 'N' in value:  # Number
                        converted_item[key] = float(value['N'])
                    elif 'BOOL' in value:  # Boolean
                        converted_item[key] = value['BOOL']
                    elif 'L' in value:  # List
                        converted_item[key] = [cls._convert_dynamodb_value(v) for v in value['L']]
                    elif 'M' in value:  # Map
                        converted_item[key] = {k: cls._convert_dynamodb_value(v) for k, v in value['M'].items()}
                    elif 'NULL' in value:  # Null
                        converted_item[key] = None
                converted_items.append(converted_item)
            
            # Create DataFrame
            df = pd.DataFrame(converted_items)
            return df
        except Exception as e:
            logger.error(f"Error converting DynamoDB results to DataFrame: {str(e)}")
            return pd.DataFrame()


    # ## Usage example: ###
    # # Create session and get DynamoDB client
    # session = aws_clien_manager.create_session()
    # dynamodb_client = aws_clien_manager.activate_dynamodb_client(session)

    # Example 1: Query with contains in filter expression
    # key_condition = 'id = :id'
    # filter_expr = 'contains(name, :search_term)'
    # filter_expr = 'key = :key'
    # expr_values = {':key': {'S': '1168'}}

    # items = dynamodb_operations_manager.scan_table(
    #     dynamodb_client,
    #     'lookup',
    #     filter_expr,
    #     expr_values
    # )

    # # Example 2: Scan with contains in filter expression
    # filter_expr = 'contains(description, :search_term)'
    # expr_values = {
    #     ':search_term': {'S': 'important'}
    # }
    # items = dynamodb_operations_manager.scan_table(
    #     dynamodb_client,
    #     'my-table',
    #     filter_expr,
    #     expr_values
    # )

    # # Example 3: Contains in a set
    # filter_expr = 'key = :key'
    # expr_values = {
    #     ':key': {'S': '1168'}
    # }

    # items = dynamodb_operations_manager.scan_table(
    #     dynamodb_client,
    #     'lookup',         # Table name as in the screenshot
    #     filter_expr,
    #     expr_values
    # )


    # items = dynamodb_operations_manager.scan_table(
    #     dynamodb_client,
    #     'lookup',
    #     limit=1  
    # )

    # for item in items:
    #     logger.info(item)


    # # Close all clients
    # aws_clien_manager.close_all_clients()

    # logger.info("Hi")
