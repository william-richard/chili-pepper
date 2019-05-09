import boto3
import pytest
from moto.awslambda import mock_lambda
from moto.cloudformation import mock_cloudformation
from moto.iam import mock_iam
from moto.kms import mock_kms
from moto.s3 import mock_s3


@pytest.fixture(autouse=True)
def apply_moto_mocks():
    with mock_cloudformation(), mock_iam(), mock_s3(), mock_lambda(), mock_kms():
        boto3.setup_default_session()
        yield None
