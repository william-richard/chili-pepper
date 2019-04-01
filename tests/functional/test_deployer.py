import zipfile

import pytest
from kale.app import Kale
from kale.deployer import Deployer
import boto3


def _create_app_structure(tmp_path):
    app_dir = tmp_path / 'app'
    app_dir.mkdir()

    app_py = app_dir / 'app.py'
    app_py_body = """
    # Test app
    def hello_world():
        print "Hello!"
    """
    # python 2.7 compatibility
    # https://stackoverflow.com/a/50139419
    if hasattr(app_py_body, 'decode'):
        app_py_body = app_py_body.decode('utf8')
    app_py.write_text(app_py_body, encoding='utf8')

    return app_dir


def _create_kale_s3_bucket():
    # type: () -> str
    import boto3
    s3_client = boto3.client('s3')
    bucket_name = 'kale_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)
    # TODO make this optional, so we can test that our code can gracefully handle when bucket versioning is not enabled
    s3_client.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"})
    return bucket_name


def test_zip(tmp_path):
    app = Kale('test_deployer_app', bucket_name='dummy', runtime='python3.7')
    deployer = Deployer(app=app)
    app_dir = _create_app_structure(tmp_path)

    deployer._create_deployment_package(tmp_path, app_dir)

    # There should now be a zip file created.
    zipfile.is_zipfile(str(tmp_path / (app.app_name + '.zip')))


def test_send_to_s3(tmp_path):
    # TODO test s3 bucket versioning
    app_dir = _create_app_structure(tmp_path)
    bucket_name = _create_kale_s3_bucket()

    app = Kale('test_deployer_app', bucket_name=bucket_name, runtime='python3.7')
    deployer = Deployer(app=app)

    s3_client = boto3.client('s3')

    deployment_package_path = deployer._create_deployment_package(tmp_path, app_dir)
    deployment_package_code_prop = deployer._send_deployment_package_to_s3(deployment_package_path)

    actual_get_object_response = s3_client.get_object(
        Bucket=bucket_name, Key=deployment_package_code_prop.S3Key, VersionId=deployment_package_code_prop.S3ObjectVersion)

    assert actual_get_object_response["VersionId"] == '0'
    assert actual_get_object_response['Body'].read() == deployment_package_path.read_bytes()


@pytest.mark.parametrize('runtime', ["python2.7", "python3.6", "python3.7"])
@pytest.mark.skip()  # Moto is being stupid - don't rely on it for now
def test_simple_lambda_deploy(tmp_path, runtime):
    app_dir = _create_app_structure(tmp_path)
    bucket_name = _create_kale_s3_bucket()

    cf_client = boto3.client('cloudformation')
    iam_resource = boto3.resource('iam')
    lambda_client = boto3.client('lambda')

    app = Kale(app_name="test_deployer_app", bucket_name=bucket_name, runtime=runtime)
    app._function_handles = ['app.hello_world']  # TODO undo this private member access hack? Or just mock the Kale app object

    deployer = Deployer(app=app)

    deployer.deploy(tmp_path, app_dir)

    cf_stack_name = app.app_name

    role_detail = cf_client.describe_stack_resource(StackName=cf_stack_name, LogicalResourceId="FunctionRole")['StackResourceDetail']
    # the Physical ID returned by CF for an IAM role is the role id, not the role name, which is basically useless
    function_role = [r for r in iam_resource.roles.all() if r.role_id == role_detail['PhysicalResourceId']][0]

    # I think moto is messing up the quotes so this is not valid json :(
    assert function_role.assume_role_policy_document == ("{'Statement': "
                                                         "[{'Action': ['sts:AssumeRole'],"
                                                         "'Effect': 'Allow',"
                                                         "'Principal': {'Service': ['lambda.amazonaws.com']"
                                                         "}}]}")

    lambda_function = lambda_client.get_function(FunctionName=("test_deployer_app.hello_world"))
    print(lambda_function)
    '''
    expected_function_attributes = {
        'FunctionName': 'test_deployer_app.app.hello_world',
        'Runtime': 'python3.7',
        'Handler': 'app.hello_world',
        'Role': {
            'Ref': 'FunctionRole'
        }
    }
    for expected_attribute, expected_value in expected_function_attributes.items():
        assert expected_attribute in template_dict['Resources']['TestDeployerAppAppHelloWorld']['Properties'].keys()
        assert template_dict['Resources']['TestDeployerAppAppHelloWorld']['Properties'][expected_attribute] == expected_value
    '''
