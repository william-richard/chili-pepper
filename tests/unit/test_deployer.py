from copy import deepcopy

import awacs
import pytest
from troposphere import awslambda, iam

from chili_pepper.app import AwsAllowPermission, ChiliPepper
from chili_pepper.config import Config
from chili_pepper.deployer import Deployer

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable


def _get_cloudformation_template_with_test_setup(config, task_kwargs):
    """
    A helper function for all of the tests that use the deployer cloudformation template

    Args:
        config (Config): The config object to use with the Chili-Pepper App
        task_kwargs (Dict[str, Object]): Kwargs to pass to app.tasks
    """

    app = ChiliPepper().create_app(app_name="test_get_cloudformation_template", config=config)
    test_bucket_name = "my_test_bucket"
    app.conf["aws"]["bucket_name"] = test_bucket_name
    if "runtime" not in app.conf["aws"]:
        app.conf["aws"]["runtime"] = "python3.7"

    @app.task(**task_kwargs)
    def say_hello(event, context):
        # moto doesn't handle returns from lambda functions :(
        print("Hello!")

    deployer = Deployer(app=app)
    code_argument = awslambda.Code(S3Bucket=test_bucket_name, S3Key="{app_name}DeploymentPackage".format(app_name=app.app_name))
    cloudformation_template = deployer._get_cloudformation_template(code_argument)

    template_resources = cloudformation_template.resources

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
    assert say_hello_task.Handler == "tests.unit.test_deployer.say_hello"

    assert len(template_resources) == 2

    return cloudformation_template


@pytest.mark.parametrize("runtime", ["python2.7", "python3.6", "python3.7"])
def test_get_cloudformation_template_runtime(runtime):
    config = Config()
    config["aws"]["runtime"] = runtime

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=dict())

    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]
    assert function_resource.Runtime == runtime


@pytest.mark.parametrize(
    "default_environment_variables",
    [None, "fake_none", dict(), {"default_key": "default_value"}, {"default_key": "default_value", "override_key": "initial_value"}],
)
@pytest.mark.parametrize("environment_variables", [None, "fake_none", dict(), {"my_key": "my_value"}, {"override_key": "new_value", "my_key": "my_value"}])
def test_get_cloudformation_template_environment_variables(default_environment_variables, environment_variables):
    task_kwargs = dict()
    if environment_variables == "fake_none":
        task_kwargs["environment_variables"] = None
    elif environment_variables is not None:
        task_kwargs["environment_variables"] = environment_variables

    config = Config()
    if default_environment_variables == "fake_none":
        config["default_environment_variables"] = None
    elif default_environment_variables is not None:
        config["default_environment_variables"] = default_environment_variables

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=task_kwargs)

    expected_environment_variables = dict()
    if default_environment_variables not in [None, "fake_none"]:
        expected_environment_variables.update(default_environment_variables)

    if environment_variables not in [None, "fake_none"]:
        expected_environment_variables.update(environment_variables)

    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]
    if environment_variables in ["fake_none", None] and default_environment_variables in ["fake_none", None]:
        assert function_resource.Environment.to_dict() == {"Variables": dict()}
    else:
        assert function_resource.Environment.to_dict() == {"Variables": expected_environment_variables}


@pytest.mark.parametrize("memory", [None, "fake_none", 128, 3008])
def test_get_cloudformation_template_memory(memory):
    task_kwargs = dict()
    if memory == "fake_none":
        task_kwargs["memory"] = None
    elif memory is not None:
        task_kwargs["memory"] = memory

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=Config(), task_kwargs=task_kwargs)
    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]
    if memory == "fake_none" or memory is None:
        assert "MemorySize" not in function_resource.to_dict()["Properties"]
    else:
        assert function_resource.MemorySize == memory


@pytest.mark.parametrize("timeout", [None, "fake_none", 1, 900])
def test_get_cloudformation_template_timeout(timeout):
    task_kwargs = dict()
    if timeout == "fake_none":
        task_kwargs["timeout"] = None
    elif timeout is not None:
        task_kwargs["timeout"] = timeout

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=Config(), task_kwargs=task_kwargs)
    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]

    if timeout == "fake_none" or timeout is None:
        assert "Timeout" not in function_resource.to_dict()["Properties"]
    else:
        assert function_resource.Timeout == timeout


@pytest.mark.parametrize("kms_key", [None, "fake_none", "", "my_kms_key"])
def test_get_cloudformation_template_kms_key(kms_key):
    config = Config()
    kms_key_config_key = "kms_key"
    if kms_key == "fake_none":
        config["aws"][kms_key_config_key] = None
    elif kms_key is not None:
        config["aws"][kms_key_config_key] = kms_key

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=dict())

    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]

    if kms_key == "fake_none" or kms_key is None or len(kms_key) == 0:
        assert "KmsKeyArn" not in function_resource.to_dict()["Properties"]
    else:
        assert function_resource.KmsKeyArn == kms_key


@pytest.mark.parametrize("kms_key", [None, "fake_none", "", "my_kms_key"])
@pytest.mark.parametrize(
    "extra_allow_permissions",
    [
        None,
        "fake_none",
        list(),
        [AwsAllowPermission(["*"], ["*"])],
        [AwsAllowPermission(["s3:Put*", "s3:Get*"], ["my_bucket", "my_other_bucket"]), AwsAllowPermission(["ec2:*"], ["*"])],
    ],
)
def test_get_cloudformation_template_permissions(kms_key, extra_allow_permissions):
    config = Config()

    aws_permissions_config_key = "extra_allow_permissions"
    if extra_allow_permissions == "fake_none":
        config["aws"][aws_permissions_config_key] = None
    elif extra_allow_permissions is not None:
        config["aws"][aws_permissions_config_key] = deepcopy(extra_allow_permissions)

    kms_key_config_key = "kms_key"
    if kms_key == "fake_none":
        config["aws"][kms_key_config_key] = None
    elif kms_key is not None:
        config["aws"][kms_key_config_key] = kms_key
        if not isinstance(extra_allow_permissions, Iterable) or isinstance(extra_allow_permissions, str):
            extra_allow_permissions = list()
        if len(kms_key) > 0:
            extra_allow_permissions.append(AwsAllowPermission(["kms:Decrypt"], [kms_key], sid="ChiliPepperGrantAccessToKmsKey"))

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=dict())

    function_role = cloudformation_template.resources["FunctionRole"]

    if extra_allow_permissions == "fake_none" or extra_allow_permissions is None or len(extra_allow_permissions) == 0:
        assert "Policies" not in function_role.to_dict()["Properties"]
    else:
        assert len(function_role.Policies) == 1
        assert (
            function_role.Policies[0].to_dict()
            == iam.Policy(
                PolicyName="ExtraChiliPepperPermissions", PolicyDocument=awacs.aws.Policy(Statement=[p.statement() for p in extra_allow_permissions])
            ).to_dict()
        )


@pytest.mark.parametrize(
    "default_tags", [None, "fake_none", dict(), {"default_key": "default_value"}, {"default_key": "default_value", "override_key": "initial_value"}]
)
@pytest.mark.parametrize(
    "function_tags", [None, "fake_none", dict(), {"tag_key": "tag_value"}, {"function_key": "function_value", "override_key": "new_value"}]
)
def test_get_cloudformation_template_function_tags(default_tags, function_tags):
    task_kwargs = dict()
    if function_tags == "fake_none":
        task_kwargs["tags"] = None
    elif function_tags is not None:
        task_kwargs["tags"] = function_tags

    config = Config()
    if default_tags == "fake_none":
        config["aws"]["default_tags"] = None
    elif default_tags is not None:
        config["aws"]["default_tags"] = default_tags

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=task_kwargs)
    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]

    expected_tags_dict = dict()
    if default_tags not in ["fake_none", None]:
        expected_tags_dict.update(default_tags)
    if function_tags not in ["fake_none", None]:
        expected_tags_dict.update(function_tags)

    if function_tags in ["fake_none", None] and default_tags in ["fake_none", None]:
        expected_tags = list()
    else:
        expected_tags = [{"Key": k, "Value": v} for k, v in expected_tags_dict.items()]
    assert sorted(function_resource.Tags.to_dict(), key=lambda d: d["Key"]) == sorted(expected_tags, key=lambda d: d["Key"])


@pytest.mark.parametrize("security_group_ids", [None, "fake_none", [], ["sg-01"], ["sg-10", "sg-11", "sg-12"]])
@pytest.mark.parametrize("subnet_ids", [None, "fake_none", [], ["subnet-01"], ["subnet-11", "subnet-12", "subnet-13"]])
def test_get_cloudformation_template_vpc_config(security_group_ids, subnet_ids):
    config = Config()
    if security_group_ids == "fake_none":
        config["aws"]["security_group_ids"] = None
    elif security_group_ids is not None:
        config["aws"]["security_group_ids"] = security_group_ids

    if subnet_ids == "fake_none":
        config["aws"]["subnet_ids"] = None
    elif subnet_ids is not None:
        config["aws"]["subnet_ids"] = subnet_ids

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=config, task_kwargs=dict())
    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]

    if security_group_ids in [None, "fake_none", []] and subnet_ids in [None, "fake_none", []]:
        assert "VpcConfig" not in function_resource.to_dict()["Properties"]
    else:
        expected_vpc_config = awslambda.VPCConfig()
        if security_group_ids in [None, "fake_none"]:
            expected_vpc_config.SecurityGroupIds = list()
        else:
            expected_vpc_config.SecurityGroupIds = security_group_ids
        if subnet_ids in [None, "fake_none"]:
            expected_vpc_config.SubnetIds = list()
        else:
            expected_vpc_config.SubnetIds = subnet_ids

        assert function_resource.VpcConfig.to_dict() == expected_vpc_config.to_dict()


@pytest.mark.parametrize("tracing_value", [None, "fake_none", True, False, 0, 1, "", "Active"])
def test_get_cloudformation_template_tracing(tracing_value):
    task_kwargs = dict()
    if tracing_value == "fake_none":
        task_kwargs["activate_tracing"] = None
    elif tracing_value is not None:
        task_kwargs["activate_tracing"] = tracing_value

    cloudformation_template = _get_cloudformation_template_with_test_setup(config=Config(), task_kwargs=task_kwargs)
    function_resource = cloudformation_template.resources["TestsUnitTestDeployerSayHello"]

    # ONLY accept True.  Any other value should result in False

    if tracing_value is True:
        expected_tracing_config = awslambda.TracingConfig(Mode="Active")
        assert function_resource.TracingConfig.to_dict() == expected_tracing_config.to_dict()
    else:
        assert "TracingConfig" not in function_resource.to_dict()["Properties"]
