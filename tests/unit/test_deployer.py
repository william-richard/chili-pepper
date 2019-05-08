import pytest
from troposphere import awslambda, iam
import awacs
import pprint

from chili_pepper.app import ChiliPepper
from chili_pepper.deployer import Deployer


@pytest.mark.parametrize("runtime", ["python2.7", "python3.6", "python3.7"])
@pytest.mark.parametrize("environment_variables", [None, "fake_none", dict(), {"my_key": "my_value"}])
@pytest.mark.parametrize("kms_key", [None, "fake_none", "", "my_kms_key"])
def test_get_cloudformation_template(runtime, environment_variables, kms_key):
    app = ChiliPepper().create_app(app_name="test_get_cloudformation_template")
    test_bucket_name = "my_test_bucket"
    app.conf["aws"]["bucket_name"] = test_bucket_name
    app.conf["aws"]["runtime"] = runtime

    kms_key_config_key = "kms_key"
    if kms_key == "fake_none":
        app.conf["aws"][kms_key_config_key] = None
    elif kms_key:
        app.conf["aws"][kms_key_config_key] = kms_key

    task_kwargs = dict()
    if environment_variables == "fake_none":
        task_kwargs["environment_variables"] = None
    elif environment_variables:
        task_kwargs["environment_variables"] = environment_variables

    @app.task(**task_kwargs)
    def say_hello(event, context):
        # moto doesn't handle returns from lambda functions :(
        print("Hello!")

    deployer = Deployer(app=app)
    code_argument = awslambda.Code(S3Bucket=test_bucket_name, S3Key="{app_name}DeploymentPackage".format(app_name=app.app_name))
    cloudformation_template = deployer._get_cloudformation_template(code_argument)

    template_resources = cloudformation_template.resources
    pprint.pprint(template_resources)

    function_role = template_resources["FunctionRole"]
    assert type(function_role) == iam.Role
    assert function_role.ManagedPolicyArns == ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
    assert function_role.AssumeRolePolicyDocument == awacs.aws.Policy(
        Statement=[
            awacs.aws.Statement(Effect=awacs.aws.Allow, Action=[awacs.sts.AssumeRole], Principal=awacs.aws.Principal("Service", ["lambda.amazonaws.com"]))
        ]
    )

    say_hello_task = template_resources["TestsUnitTestDeployerSayHello"]
    assert type(say_hello_task) == awslambda.Function
    assert say_hello_task.Code == code_argument
    assert say_hello_task.Runtime == runtime
    assert say_hello_task.Handler == "tests.unit.test_deployer.say_hello"
    if environment_variables == "fake_none" or environment_variables is None:
        assert say_hello_task.Environment.to_dict() == {"Variables": dict()}
    else:
        assert say_hello_task.Environment.to_dict() == {"Variables": environment_variables}

    if kms_key == "fake_none" or kms_key is None or len(kms_key) == 0:
        assert "KmsKeyArn" not in say_hello_task.to_dict()["Properties"]
    else:
        assert say_hello_task.KmsKeyArn == kms_key

    assert len(template_resources) == 2
