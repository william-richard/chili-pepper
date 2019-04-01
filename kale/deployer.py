import os
import re
import zipfile

import boto3

from awacs.aws import Allow, Policy, Principal, Statement
from awacs.sts import AssumeRole
from troposphere import Ref, Template, awslambda, iam

from kale.app import Kale

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

try:
    from typing import List
except ImportError:
    # typing isn't in python2.7 and I don't want to deal with fixing it right now
    pass

TITLE_SPLIT_REGEX_HACK = re.compile("[^a-zA-Z0-9]")


class Deployer:
    def __init__(self, app):
        # type: (Kale) -> None
        self._app = app

    def deploy(self, dest, app_dir):
        # type: (Path, Path, Kale) -> str

        deployment_package_path = self._create_deployment_package(dest, app_dir)
        deployment_package_code_prop = self._send_deployment_package_to_s3(deployment_package_path)
        cf_template = self._get_cloudformation_template(deployment_package_code_prop)

        cf_client = boto3.client('cloudformation')
        # TODO eventually we'll want to use s3 hosted templates, to have bigger stacks
        # TODO this is a bad stack name
        create_stack_response = cf_client.create_stack(StackName=self._app.app_name, TemplateBody=cf_template.to_json())
        return create_stack_response['StackId']

    def _create_deployment_package(self, dest, app_dir):
        # type: (Path, Path) -> Path
        """
        Builds a deployment package of the application

        TODO add support for requirements
        """
        output_filename = dest / (self._app.app_name + '.zip')

        zfh = zipfile.ZipFile(str(output_filename), 'w', zipfile.ZIP_DEFLATED)

        for root, _, files in os.walk(str(app_dir)):
            for file in files:
                zfh.write(os.path.join(root, file))
        zfh.close()
        return output_filename

    def _send_deployment_package_to_s3(self, deployment_package_path):
        # type: (Path) -> awslambda.Code
        # TODO verify that bucket has versioning enabled
        s3_key = self._app.app_name + "_deployment_package.zip"
        s3_client = boto3.client('s3')

        s3_response = s3_client.put_object(
            Bucket=self._app.bucket_name,
            Key=s3_key,
            Body=deployment_package_path.read_bytes(),
        )

        return awslambda.Code(S3Bucket=self._app.bucket_name, S3Key=s3_key, S3ObjectVersion=s3_response['VersionId'])

    def _get_cloudformation_template(self, code_property):
        # type: (awslambda.Code, List[str], str) -> Template
        template = Template()

        role = self._create_role()
        template.add_resource(role)

        for function_handler_string in self._app.function_handles:
            template.add_resource(self._create_lambda_function(code_property, function_handler_string, role, self._app.runtime))

        return template

    def _create_lambda_function(self, code_property, function_handler_string, role, runtime):
        # type: (awslambda.Code, str, iam.Role, str) -> None
        # TODO handle more than one function
        # TODO customizable memory and other attributes
        function_name = self._app.app_name + "." + function_handler_string  # TODO this is not a good choice
        title = ''.join(part.capitalize() for part in TITLE_SPLIT_REGEX_HACK.split(function_name))  # TODO this will not work in general
        return awslambda.Function(
            title,
            Code=code_property,
            FunctionName=function_name,
            Handler=function_handler_string,
            Role=Ref(role),
            Runtime=runtime,
        )

    def _create_role(self):
        # TODO set a role name here? Instead of relying on cloudformation to create a random nonsense string for the name
        return iam.Role(
            "FunctionRole",
            AssumeRolePolicyDocument=Policy(Statement=[Statement(Effect=Allow, Action=[AssumeRole], Principal=Principal("Service", ["lambda.amazonaws.com"]))]))
