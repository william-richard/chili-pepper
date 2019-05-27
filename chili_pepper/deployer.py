import builtins
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import awacs
import boto3
import troposphere
from awacs.aws import Allow, Principal, Statement
from awacs.sts import AssumeRole
from troposphere import GetAtt, Template, awslambda, iam

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

try:
    from typing import List, TYPE_CHECKING

    if TYPE_CHECKING:
        from app import TaskFunction
except ImportError:
    # typing isn't in python2.7 and I don't want to deal with fixing it right now
    pass

TITLE_SPLIT_REGEX_HACK = re.compile("[^a-zA-Z0-9]")


class Deployer:
    def __init__(self, app):
        # type: (app.ChiliPepper) -> None
        """
        Args:
            app (app.ChiliPepper): The Chili-Pepper app to be deployed
        """
        self._app = app

        self._logger = logging.getLogger(__name__)

    def deploy(self, dest, app_dir):
        # type: (Path, Path) -> str
        """Deploys the chili-pepper app

        Args:
            dest (Path): The destination for the deployment package.
            app_dir (Path): The location of the application source code.

        Returns:
            str: The cloudformation template that was deployed to AWS.
        """
        self._logger.info("Starting to deploy")

        deployment_package_path = self._create_deployment_package(dest, app_dir)
        deployment_package_code_prop = self._send_deployment_package_to_s3(deployment_package_path)
        cf_template = self._get_cloudformation_template(deployment_package_code_prop)
        return self._deploy_template_to_cloudformation(cf_template)

    def get_function_id(self, python_function):
        # type: (builtins.function) -> str
        """Get a unique identifier for the serverless function

        Args:
            python_function (builtins.function): The python function.  Must have been included in the Chili-Pepper app.

        Returns:
            str: The unique serverless function identification string
        """
        # TODO it's a little weird that this lives on the deployer - I'm not sure what the right abstraction is
        lambda_function_cf_logical_id = self._get_function_logical_id(self._get_function_handler_string(python_function))
        stack_name = self._get_stack_name()

        cf_client = boto3.client("cloudformation")
        describe_function_resource_response = cf_client.describe_stack_resource(StackName=stack_name, LogicalResourceId=lambda_function_cf_logical_id)
        lambda_function_name = describe_function_resource_response["StackResourceDetail"]["PhysicalResourceId"]

        return lambda_function_name

    def _create_deployment_package(self, dest, app_dir):
        # type: (Path, Path) -> Path
        """Builds a deployment package of the application

        Args:
            dest (Path): The deployment package destination
            app_dir (Path): The application source code location

        Returns:
            Path: The location of the deployment package zipfile
        """
        output_filename = dest / (self._app.app_name + ".zip")
        self._logger.info("Creating deployment package" + str(output_filename))

        zfh = zipfile.ZipFile(str(output_filename), "w", zipfile.ZIP_DEFLATED)

        def _add_directory_to_archive(src_dir):
            for root, _, files in os.walk(src_dir):
                for _file in files:
                    file_path = os.path.join(root, _file)
                    # do not put files under the app_dir inside the zip
                    # without passing arcname, the archive will have the app_dir folder at its root
                    zip_path = os.path.relpath(file_path, str(src_dir))
                    self._logger.debug("Adding " + file_path + " to archive at " + zip_path)
                    zfh.write(file_path, arcname=zip_path)

        # TODO un-hardcode the requirements.txt path
        requirements_path = app_dir / "requirements.txt"
        if requirements_path.exists():
            requirements_temp_dir = tempfile.mkdtemp(prefix="chili-pepper-")
            try:
                self._logger.info(
                    "Installing requirements into temporary directory " + requirements_temp_dir + "so they can be included in the deployment package"
                )
                # TODO gracefully handle requirements with -e
                # https://github.com/UnitedIncome/serverless-python-requirements/issues/240
                # https://github.com/nficano/python-lambda/blob/master/aws_lambda/aws_lambda.py#L417
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_path.resolve()), "-t", requirements_temp_dir, "--ignore-installed"]
                )
                _add_directory_to_archive(requirements_temp_dir)
                self._logger.info("Done installing requirements and adding them to the deployment package")
            finally:
                shutil.rmtree(requirements_temp_dir)

        self._logger.info("Adding application code to the deployment package")
        _add_directory_to_archive(str(app_dir))

        zfh.close()

        self._logger.info("Done creating deployment package " + str(output_filename))

        return output_filename

    def _send_deployment_package_to_s3(self, deployment_package_path):
        # type: (Path) -> awslambda.Code
        # TODO verify that bucket has versioning enabled
        # TODO do not push a new zip if it is identical to the current version
        # TODO do not push a new zip if it is identical to an old version - just use the old version
        s3_key = self._app.app_name + "_deployment_package.zip"
        self._logger.info("Sending deployment package to s3.  bucket: '" + self._app.bucket_name + "'. key: '" + s3_key + "'.")

        s3_client = boto3.client("s3")

        s3_response = s3_client.put_object(Bucket=self._app.bucket_name, Key=s3_key, Body=deployment_package_path.read_bytes())

        self._logger.info("Done sending deployment package to s3. bucket: '" + self._app.bucket_name + "'. key: '" + s3_key + "'.")

        return awslambda.Code(S3Bucket=self._app.bucket_name, S3Key=s3_key, S3ObjectVersion=s3_response["VersionId"])

    def _get_cloudformation_template(self, code_property):
        # type: (awslambda.Code, List[str], str) -> Template
        self._logger.info("Generating cloudformation template")
        template = Template()

        role = self._create_role()
        template.add_resource(role)

        for task_function in self._app.task_functions:
            template.add_resource(self._create_lambda_function(code_property, task_function, role, self._app.runtime))

        self._logger.info("Done generating cloudformation template")
        return template

    def _get_function_handler_string(self, python_function):
        # type: (builtins.function) -> str
        module_name = python_function.__module__
        return module_name + "." + python_function.__name__

    def _get_function_logical_id(self, function_handler):
        # type: (str) -> str
        return "".join(part.capitalize() for part in TITLE_SPLIT_REGEX_HACK.split(function_handler))  # TODO this will not work in general

    def _create_lambda_function(self, code_property, task_function, role, runtime):
        # type: (awslambda.Code, TaskFunction, iam.Role, str) -> None
        # TODO add support for versioning
        function_handler = self._get_function_handler_string(task_function.func)
        title = self._get_function_logical_id(function_handler)

        function_kwargs = {
            "Code": code_property,
            "Handler": function_handler,
            "Role": GetAtt(role, "Arn"),
            "Runtime": runtime,
            "Environment": awslambda.Environment(Variables=task_function.environment_variables),
            "Tags": troposphere.Tags(task_function.tags),
        }
        if self._app.kms_key_arn is not None and len(self._app.kms_key_arn) > 0:
            function_kwargs["KmsKeyArn"] = self._app.kms_key_arn
        if len(self._app.subnet_ids) > 0 or len(self._app.security_group_ids) > 0:
            function_kwargs["VpcConfig"] = awslambda.VPCConfig(SubnetIds=self._app.subnet_ids, SecurityGroupIds=self._app.security_group_ids)

        if task_function.memory is not None:
            function_kwargs["MemorySize"] = task_function.memory
        if task_function.timeout is not None:
            function_kwargs["Timeout"] = task_function.timeout

        if task_function.activate_tracing:
            function_kwargs["TracingConfig"] = awslambda.TracingConfig(Mode="Active")

        # TODO specify the function name?  Maybe we don't care?
        return awslambda.Function(title, **function_kwargs)

    def _create_role(self):
        # TODO set a role name here? Instead of relying on cloudformation to create a random nonsense string for the name
        role_kwargs = {
            "AssumeRolePolicyDocument": awacs.aws.Policy(
                Statement=[Statement(Effect=Allow, Action=[AssumeRole], Principal=Principal("Service", ["lambda.amazonaws.com"]))]
            ),
            "ManagedPolicyArns": ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
        }
        if len(self._app.allow_policy_permissions) > 0:
            role_kwargs["Policies"] = [
                iam.Policy(
                    PolicyName="ExtraChiliPepperPermissions",
                    PolicyDocument=awacs.aws.Policy(Statement=[p.statement() for p in self._app.allow_policy_permissions]),
                )
            ]

        return iam.Role("FunctionRole", **role_kwargs)

    def _get_stack_name(self):
        # type: () -> str
        # TODO this is a bad stack name
        return self._app.app_name

    def _deploy_template_to_cloudformation(self, cf_template):
        cf_stack_name = self._get_stack_name()

        self._logger.info("Deploying cloudformation template to stack " + cf_stack_name)

        cf_client = boto3.client("cloudformation")
        # TODO start using s3 hosted templates, to have bigger stacks
        try:
            cf_client.describe_stacks(StackName=cf_stack_name)

            stack_exists = True
        except cf_client.exceptions.ClientError:
            stack_exists = False

        if stack_exists:
            # stack exists
            update_stack_response = cf_client.update_stack(StackName=cf_stack_name, TemplateBody=cf_template.to_json(), Capabilities=["CAPABILITY_IAM"])
            stack_id = update_stack_response["StackId"]
            self._logger.info("Cloudformation stack '" + cf_stack_name + "' with id " + stack_id + " update in progress")
        else:
            # stack does not exist - create it
            create_stack_response = cf_client.create_stack(StackName=cf_stack_name, TemplateBody=cf_template.to_json(), Capabilities=["CAPABILITY_IAM"])
            stack_id = create_stack_response["StackId"]
            self._logger.info("Cloudformation stack '" + cf_stack_name + "' with id " + stack_id + " creation in progress")

        # TODO track stack update/create and give feedback if it succeeds or fails

        return stack_id
