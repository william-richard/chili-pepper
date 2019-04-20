import argparse
import boto3
import pytest
import pprint
import json
from collections import OrderedDict

from conftest import create_app_structure, create_kale_s3_bucket
from kale.main import CLI


@pytest.mark.parametrize("runtime", ["python2.7", "python3.6", "python3.7"])
def test_deploy(tmp_path, request, runtime):
    bucket_name = create_kale_s3_bucket()
    app_dir = create_app_structure(tmp_path, bucket_name=bucket_name, runtime=runtime, pytest_request_fixture=request)

    cli = CLI()
    fake_args = argparse.Namespace(app="tasks.app", app_dir=str(app_dir), deployment_package_dir=str(tmp_path))
    cli.deploy(args=fake_args)

    lambda_client = boto3.client("lambda")
    lambda_list_functions_response = lambda_client.list_functions()

    assert len(lambda_list_functions_response["Functions"]) == 1
    my_function = lambda_list_functions_response["Functions"][0]

    print("Full function dictionary:")
    pprint.pprint(my_function)

    expected_function_attributes = {
        "Runtime": runtime,
        "Handler": "tasks.say_hello",
        "Role": {"Fn::GetAtt": ["FunctionRole", "Arn"]},  # this is moto's mock not resolving GetAtt
    }

    for expected_attribute, expected_value in expected_function_attributes.items():
        assert expected_attribute in my_function
        assert my_function[expected_attribute] == expected_value

    iam_resource = boto3.resource("iam")
    all_roles = list(iam_resource.roles.all())

    assert len(all_roles) == 1
    my_role = all_roles[0]
    print("Full role from list_roles:")
    pprint.pprint(my_role)

    assert json.loads(my_role.assume_role_policy_document.replace("'", '"')) == {
        "Statement": [{"Action": ["sts:AssumeRole"], "Effect": "Allow", "Principal": {"Service": ["lambda.amazonaws.com"]}}]
    }
    # TOOO moto does not handle attaching the lambda execution role policy correctly....
    assert list(my_role.attached_policies.all()) == []


@pytest.mark.parametrize("runtime", ["python2.7", "python3.6", "python3.7"])
def test_deployed_cf_template(tmp_path, request, runtime):
    bucket_name = create_kale_s3_bucket()
    app_dir = create_app_structure(tmp_path, bucket_name=bucket_name, runtime=runtime, pytest_request_fixture=request)

    cli = CLI()
    fake_args = argparse.Namespace(app="tasks.app", app_dir=str(app_dir), deployment_package_dir=str(tmp_path))
    cli.deploy(args=fake_args)

    cf_client = boto3.client("cloudformation")
    list_stacks_response = cf_client.list_stacks()

    assert len(list_stacks_response["StackSummaries"]) == 1
    stack_summary = list_stacks_response["StackSummaries"][0]
    stack_name = stack_summary["StackName"]

    stack_template = cf_client.get_template(StackName=stack_name)["TemplateBody"]
    stack_resources = stack_template["Resources"]

    pprint.pprint(stack_template)

    lambda_function_role = stack_resources["FunctionRole"]
    assert lambda_function_role["Type"] == "AWS::IAM::Role"
    lambda_function_role_properties = lambda_function_role["Properties"]
    assert lambda_function_role_properties["ManagedPolicyArns"] == ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
    assert lambda_function_role_properties["AssumeRolePolicyDocument"] == OrderedDict(
        [
            (
                "Statement",
                [OrderedDict([("Action", ["sts:AssumeRole"]), ("Effect", "Allow"), ("Principal", OrderedDict([("Service", ["lambda.amazonaws.com"])]))])],
            )
        ]
    )

    lambda_function = stack_resources["TasksSayHello"]
    assert lambda_function["Type"] == "AWS::Lambda::Function"
    lambda_function_properties = lambda_function["Properties"]
    assert lambda_function_properties["Code"] == OrderedDict([("S3Bucket", bucket_name), ("S3Key", "demo_deployment_package.zip"), ("S3ObjectVersion", "0")])
    assert lambda_function_properties["Runtime"] == runtime
    assert lambda_function_properties["Handler"] == "tasks.say_hello"

    assert len(stack_resources) == 2
