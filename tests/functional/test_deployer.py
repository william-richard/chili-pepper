import zipfile
import boto3

from conftest import create_app_structure, create_chili_pepper_s3_bucket
from chili_pepper.app import ChiliPepper
from chili_pepper.deployer import Deployer


def test_zip(tmp_path, request):
    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = "dummy"
    app.conf["aws"]["runtime"] = "python3.7"

    deployer = Deployer(app=app)
    app_dir = create_app_structure(tmp_path, pytest_request_fixture=request)

    deployer._create_deployment_package(tmp_path, app_dir)

    # There should now be a zip file created.
    zipfile.is_zipfile(str(tmp_path / (app.app_name + ".zip")))


def test_send_to_s3(tmp_path, request):
    # TODO test s3 bucket versioning
    bucket_name = create_chili_pepper_s3_bucket()
    app_dir = create_app_structure(tmp_path, bucket_name=bucket_name, pytest_request_fixture=request)

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    deployer = Deployer(app=app)

    s3_client = boto3.client("s3")

    deployment_package_path = deployer._create_deployment_package(tmp_path, app_dir)
    deployment_package_code_prop = deployer._send_deployment_package_to_s3(deployment_package_path)

    actual_get_object_response = s3_client.get_object(
        Bucket=bucket_name, Key=deployment_package_code_prop.S3Key, VersionId=deployment_package_code_prop.S3ObjectVersion
    )

    assert actual_get_object_response["VersionId"] == "0"
    assert actual_get_object_response["Body"].read() == deployment_package_path.read_bytes()
