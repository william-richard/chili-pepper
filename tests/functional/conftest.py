import pytest
from moto import mock_lambda, mock_cloudformation, mock_iam, mock_s3
import boto3


@pytest.fixture(autouse=True)
def apply_moto_mocks():
    with mock_lambda(), mock_cloudformation(), mock_iam(), mock_s3():
        boto3.setup_default_session()
        yield None


def create_kale_s3_bucket():
    # type: () -> str
    import boto3

    s3_client = boto3.client("s3")
    bucket_name = "kale_test_bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    # TODO make this optional, so we can test that our code can gracefully handle when bucket versioning is not enabled
    s3_client.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"})
    return bucket_name
