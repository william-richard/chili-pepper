import awacs
import pytest

from chili_pepper.app import AwsAllowPermission, MissingArgumentError


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
