import pytest
from conftest import create_kale_s3_bucket

from kale.app import Kale, InvalidFunctionSignature


def test_task_decorator():
    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    @app.task
    def say_hello(event, context):
        return "Hello!"

    assert hasattr(say_hello, "delay")
    assert app.task_functions == [say_hello]


def test_invalid_signature_no_arguments():

    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task
        def say_hello():
            return "Hello!"


def test_invalid_signature_only_event():

    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task
        def say_hello(event):
            return "Hello!"


def test_invalid_signature_only_context():

    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task
        def say_hello(context):
            return "Hello!"


def test_invalid_signature_extra_parameter():

    bucket_name = create_kale_s3_bucket()

    app = Kale("test_deployer_app", bucket_name=bucket_name, runtime="python3.7")

    with pytest.raises(InvalidFunctionSignature):

        @app.task
        def say_hello(event, context, extra):
            return "Hello!"
