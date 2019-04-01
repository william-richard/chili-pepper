import pytest
from moto import mock_lambda, mock_cloudformation, mock_iam, mock_s3
import boto3


@pytest.fixture(autouse=True)
def apply_moto_mocks():
    with mock_lambda(), mock_cloudformation(), mock_iam(), mock_s3():
        boto3.setup_default_session()
        yield None
