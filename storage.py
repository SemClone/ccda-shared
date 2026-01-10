"""
Storage Client for DigitalOcean Spaces (S3-compatible)

Provides a unified interface for reading and writing data to Spaces.
All components (worker, API, dashboard) should use this client.
"""
import json
import logging
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import ClientError

from shared.env import get_spaces_config

logger = logging.getLogger(__name__)


class SpacesClient:
    """Client for interacting with DigitalOcean Spaces"""

    def __init__(
        self,
        key: Optional[str] = None,
        secret: Optional[str] = None,
        region: Optional[str] = None,
        bucket: Optional[str] = None
    ):
        """
        Initialize Spaces client

        Args:
            key: Spaces access key (defaults to SPACES_KEY env var)
            secret: Spaces secret key (defaults to SPACES_SECRET env var)
            region: Spaces region (defaults to SPACES_REGION env var or 'sfo3')
            bucket: Bucket name (defaults to SPACES_BUCKET env var or 'ccda-data')
        """
        config = get_spaces_config(key=key, secret=secret, region=region, bucket=bucket)
        self.key = config["key"]
        self.secret = config["secret"]
        self.region = config["region"]
        self.bucket = config["bucket"]
        self.endpoint = config["endpoint"]

        if not self.key or not self.secret:
            logger.warning("SPACES_KEY or SPACES_SECRET not set - Spaces operations may fail")

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.key,
            aws_secret_access_key=self.secret,
        )

        logger.info(
            "SpacesClient initialized: region=%s, bucket=%s, endpoint=%s",
            self.region,
            self.bucket,
            self.endpoint,
        )

    def read_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Read JSON file from Spaces

        Args:
            key: File key/path in Spaces (e.g., 'demo/status.json')

        Returns:
            Parsed JSON data as dict, or None if file doesn't exist

        Raises:
            Exception: If file exists but can't be parsed as JSON
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found in Spaces: {key}")
                return None
            else:
                logger.error(f"Error reading from Spaces: {e}")
                raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {key}: {e}")
            raise

    def write_json(self, key: str, data: Dict[str, Any], indent: int = 2) -> bool:
        """
        Write JSON data to Spaces

        Args:
            key: File key/path in Spaces
            data: Dictionary to write as JSON
            indent: JSON indentation (default: 2)

        Returns:
            True if successful, False otherwise
        """
        try:
            json_data = json.dumps(data, indent=indent)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            logger.debug(f"Successfully wrote to Spaces: {key}")
            return True
        except Exception as e:
            logger.error(f"Error writing to Spaces: {e}")
            return False

    def read_file(self, key: str) -> Optional[bytes]:
        """
        Read raw file from Spaces

        Args:
            key: File key/path in Spaces

        Returns:
            File contents as bytes, or None if file doesn't exist
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found in Spaces: {key}")
                return None
            else:
                logger.error(f"Error reading from Spaces: {e}")
                raise

    def write_file(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> bool:
        """
        Write raw file to Spaces

        Args:
            key: File key/path in Spaces
            data: File contents as bytes
            content_type: MIME type (default: application/octet-stream)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            logger.debug(f"Successfully wrote file to Spaces: {key}")
            return True
        except Exception as e:
            logger.error(f"Error writing file to Spaces: {e}")
            return False

    def download_file(self, key: str, local_path: str) -> bool:
        """
        Download file from Spaces to local filesystem

        Args:
            key: File key/path in Spaces
            local_path: Local filesystem path to save file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(self.bucket, key, local_path)
            logger.info(f"Downloaded {key} to {local_path}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"File not found in Spaces: {key}")
                return False
            else:
                logger.error(f"Error downloading from Spaces: {e}")
                return False
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def upload_file(self, local_path: str, key: str) -> bool:
        """
        Upload file from local filesystem to Spaces

        Args:
            local_path: Local filesystem path
            key: File key/path in Spaces

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(local_path, self.bucket, key)
            logger.info(f"Uploaded {local_path} to {key}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False

    def file_exists(self, key: str) -> bool:
        """
        Check if file exists in Spaces

        Args:
            key: File key/path in Spaces

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def get_file_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get file metadata from Spaces including last modified time.

        Args:
            key: File key/path in Spaces

        Returns:
            Dictionary with metadata including 'last_modified' datetime
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return {
                "last_modified": response.get('LastModified'),
                "content_length": response.get('ContentLength'),
                "etag": response.get('ETag'),
                "content_type": response.get('ContentType')
            }
        except ClientError as e:
            logger.error(f"Failed to get metadata for {key}: {e}")
            return {}

    def list_files(self, prefix: str = '') -> list[str]:
        """
        List files in Spaces with optional prefix

        Args:
            prefix: Key prefix to filter by (e.g., 'demo/')

        Returns:
            List of file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents']]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def delete_file(self, key: str) -> bool:
        """
        Delete file from Spaces

        Args:
            key: File key/path in Spaces

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted {key} from Spaces")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
