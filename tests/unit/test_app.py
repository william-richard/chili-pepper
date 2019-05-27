import awacs
import pytest
from base64 import b64encode

from chili_pepper.app import AwsAllowPermission, MissingArgumentError, Result


class TestAwsAllowPermissions:
    @pytest.mark.parametrize(
        "actions, resources", [([], []), (["*"], ["*"]), (["*"], []), ([], ["*"]), (["s3:Put*", "s3:Get*"], ["my_bucket", "my_other_bucket"])]
    )
    def test_statement(self, actions, resources):
        if len(actions) == 0 or len(resources) == 0:
            with pytest.raises(MissingArgumentError):
                AwsAllowPermission(allow_actions=actions, allow_resources=resources)
        else:
            aws_allow_permission = AwsAllowPermission(allow_actions=actions, allow_resources=resources)
            expected_statement = awacs.aws.Statement(
                Effect=awacs.aws.Allow, Action=[awacs.aws.Action(*action.split(":")) for action in actions], Resource=resources
            )
            assert aws_allow_permission.statement() == expected_statement


class TestTaskResult:
    @pytest.mark.parametrize("fake_log_result", [None, "", "hello world", "multiple\nline\nlogs"])
    def test_log_result(self, mocker, fake_log_result):
        mocker.patch.object(Result, "_join_invocation")

        result = Result("test_function", dict())

        # trick the result into thinking the lambda function was invoked
        result._invoke_response = dict()
        if fake_log_result is None:
            result._invoke_response["LogResult"] = None
        else:
            result._invoke_response["LogResult"] = b64encode(fake_log_result.encode("utf8"))

        # actual test is here - make sure thet log result is properly recovered from the invoke response
        expected_log_result = fake_log_result if fake_log_result is not None else ""
        assert result.get_log_result() == expected_log_result
