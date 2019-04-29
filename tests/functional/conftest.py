import importlib
import os
import sys

import boto3
import pytest
from moto import mock_cloudformation, mock_iam, mock_lambda, mock_s3


@pytest.fixture(autouse=True)
def apply_moto_mocks():
    with mock_cloudformation(), mock_iam(), mock_s3(), mock_lambda():
        boto3.setup_default_session()
        yield None


@pytest.fixture(autouse=True)
def reset_sys_path():
    # main.CLI.deploy can add stuff to sys.path, and load up modules that we'll want to re-import differently in subsequent tests
    # like the files created in create_app_structure
    # Resetting sys.path and the imported modules before each test will make things more reliable
    #
    # resetting sys.path probably has no effect - main.CLI.deploy should be putting new paths at the start of sys.path
    # and so the new paths will be checked first, but it doesn't hurt
    #
    # resetting sys.modules absolutely has an effect, because without this, the first instance of a module (like the test app.tasks module)
    # that was imported will be used for all the other tests.
    original_sys_path = list(sys.path)
    original_sys_modules_keys = list(sys.modules.keys())
    try:
        importlib.invalidate_caches()
    except AttributeError:
        # python2.7 does not have invalidate_caches
        pass
    yield
    # https://www.oreilly.com/library/view/python-cookbook/0596001673/ch14s02.html
    for m in list(sys.modules.keys()):
        if m not in original_sys_modules_keys:
            del sys.modules[m]
    sys.path = original_sys_path


def create_chili_pepper_s3_bucket():
    # type: () -> str
    s3_client = boto3.client("s3")
    bucket_name = "chili_pepper_test_bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    # TODO make this optional, so we can test that our code can gracefully handle when bucket versioning is not enabled
    s3_client.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"})
    return bucket_name


def create_app_structure(
    tmp_path, pytest_request_fixture, bucket_name="you_forgot_to_call_conftest.create_chili_pepper_s3_bucket", runtime="python3.7", include_requirements=False
):
    # pytest_request should be the pytest request fixture https://docs.pytest.org/en/latest/reference.html#request
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    tasks_py = app_dir / "tasks.py"
    tasks_py_body = """
from chili_pepper.app import ChiliPepper

app = ChiliPepper().create_app(app_name="demo")
app.conf['aws']['bucket_name'] = "{bucket_name}"
app.conf['aws']['runtime'] =  "{runtime}"

@app.task()
def say_hello(event, context):
    return_value = dict()
    return_value["Hello"] = "World!"
    print(return_value) # moto doesn't handle returns from lambda functions :(
    return return_value
    """.format(
        bucket_name=bucket_name, runtime=runtime
    )
    # python 2.7 compatibility
    # https://stackoverflow.com/a/50139419
    if hasattr(tasks_py_body, "decode"):
        tasks_py_body = tasks_py_body.decode("utf8")
    tasks_py.write_text(tasks_py_body, encoding="utf8")

    if include_requirements:
        # need to find the code directory, so we can tell the lambda container to install chili-pepper
        test_file_path_str = str(pytest_request_fixture.fspath)
        path_head_str, path_tail_str = os.path.split(test_file_path_str)
        while path_tail_str != "tests":
            path_head_str, path_tail_str = os.path.split(path_head_str)
        code_root_dir = path_head_str

        requirements_txt = app_dir / "requirements.txt"
        requirements_txt_body = """
    {code_root_dir}
    """.format(
            code_root_dir=code_root_dir
        )
        if hasattr(requirements_txt_body, "decode"):
            requirements_txt_body = requirements_txt_body.decode("utf8")
        requirements_txt.write_text(requirements_txt_body, encoding="utf8")

    init_py = app_dir / "__init__.py"
    init_py.touch()

    return app_dir
