import pytest
from conftest import create_app_structure, create_chili_pepper_s3_bucket

from chili_pepper.app import ChiliPepper, InvalidFunctionSignature, TaskFunction
from chili_pepper.main import CLI
from chili_pepper.deployer import Deployer


def test_task_decorator():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    @app.task()
    def say_hello(event, context):
        return "Hello!"

    assert hasattr(say_hello, "delay")
    assert app.task_functions == [TaskFunction(say_hello)]


def test_task_decorator_environment_variables():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    env_vars = {"test_app_key": "test_app_value"}

    @app.task(environment_variables=env_vars)
    def say_hello(event, context):
        return "Hello!"

    assert hasattr(say_hello, "delay")
    expected_task_function = TaskFunction(say_hello, environment_variables=env_vars)
    print(app.task_functions[0].environment_variables)
    print(expected_task_function.environment_variables)
    assert app.task_functions == [expected_task_function]


def test_app_env_vars():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    app.conf["default_environment_variables"] = {"test_app_key": "test_app_value"}

    @app.task()
    def say_hello(event, context):
        return "Hello!"

    expected_task_function = TaskFunction(say_hello, environment_variables=app.conf["default_environment_variables"])
    print(app.task_functions[0])
    print(expected_task_function)
    assert app.task_functions == [expected_task_function]


def test_task_decorator_env_var_override():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    default_key = "default_key"
    overridden_key = "im_going_to_be_overridden_key"

    app.conf["default_environment_variables"] = {overridden_key: "short_lived", default_key: "default_value"}
    task_env_vars = {overridden_key: "LONG_LIVED"}

    @app.task(environment_variables=task_env_vars)
    def say_hello(event, context):
        return "Hello!"

    expected_env_vars = {default_key: app.conf["default_environment_variables"][default_key], overridden_key: task_env_vars[overridden_key]}

    expected_task_function = TaskFunction(say_hello, environment_variables=expected_env_vars)
    print(app.task_functions[0].environment_variables)
    print(expected_task_function.environment_variables)
    assert app.task_functions == [expected_task_function]


def test_invalid_signature_no_arguments():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello():  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_only_event():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(event):  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_only_context():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(context):  # pylint: disable=unused-variable
            return "Hello!"


def test_invalid_signature_extra_parameter():
    bucket_name = create_chili_pepper_s3_bucket()

    app = ChiliPepper().create_app("test_deployer_app")
    app.conf["aws"]["bucket_name"] = bucket_name
    app.conf["aws"]["runtime"] = "python3.7"

    with pytest.raises(InvalidFunctionSignature):

        @app.task()
        def say_hello(event, context, extra):  # pylint: disable=unused-variable
            return "Hello!"


def test_delay_function(tmp_path, request):
    # `request` is the pytest request fixture https://docs.pytest.org/en/latest/reference.html#request
    bucket_name = create_chili_pepper_s3_bucket()
    app_dir = create_app_structure(tmp_path, request, bucket_name=bucket_name, include_requirements=True)

    cli = CLI()
    app = cli._load_app("tasks.app", str(app_dir))
    deployer = Deployer(app)
    deployer.deploy(tmp_path, app_dir)

    say_hello_function = [f.func for f in app.task_functions if f.func.__name__ == "say_hello"][0]
    say_hello_result = say_hello_function.delay({})

    # moto doesn't handle return :(
    say_hello_result.get()
    assert say_hello_result._invoke_response["StatusCode"] == 202
