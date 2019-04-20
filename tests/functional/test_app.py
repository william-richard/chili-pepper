import pytest
from conftest import create_kale_s3_bucket, create_app_structure

from kale.app import Kale, InvalidFunctionSignature
from kale.main import CLI
from kale.deployer import Deployer


def test_task_decorator():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    @app.task()
    def say_hello(event, context):
        return "Hello!"

    assert hasattr(say_hello, "delay")
    assert app.task_functions == [say_hello]


def test_invalid_signature_no_arguments():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello():  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_only_event():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(event):  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_only_context():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(context):  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_extra_parameter():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(event, context, extra):  # pylint: disable=unused-variable
            return "Hello!"


def test_delay_function(tmp_path, request):
    # `request` is the pytest request fixture https://docs.pytest.org/en/latest/reference.html#request
    bucket_name = create_kale_s3_bucket()
    app_dir = create_app_structure(tmp_path, request, bucket_name=bucket_name, include_requirements=True)

    cli = CLI()
    app = cli._load_app("tasks.app", str(app_dir))
    deployer = Deployer(app)
    deployer.deploy(tmp_path, app_dir)

    say_hello_function = [f for f in app.task_functions if f.__name__ == "say_hello"][0]
    say_hello_result = say_hello_function.delay({})

    # moto doesn't handle return :(
    say_hello_result.get()
    assert say_hello_result._invoke_response["StatusCode"] == 202
