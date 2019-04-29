import builtins
import inspect
import boto3
from enum import Enum
import json
import logging
from threading import Thread

from chili_pepper.exception import ChiliPepperException
from chili_pepper.deployer import Deployer
from chili_pepper.config import Config

try:
    from typing import List, Optional, Dict
except ImportError:
    # python2.7 doesn't have typing, and I don't want to mess with mypy yet
    pass


class InvalidFunctionSignature(ChiliPepperException):
    pass


class InvocationError(ChiliPepperException):
    pass


class Result:
    def __init__(self, lambda_function_name, event):
        # type: (str, dict) -> None
        self._logger = logging.getLogger(__name__)

        self._lambda_function_name = lambda_function_name
        self._event = event

        self._thread = None
        self._invoke_response = None

    def start(self):
        if self._thread is None:

            def lambda_run():
                lambda_client = boto3.client("lambda")
                self._invoke_response = lambda_client.invoke(FunctionName=self._lambda_function_name, Payload=json.dumps(self._event))
                return

            self._thread = Thread(target=lambda_run)
            self._thread.start()
        return self._thread

    def get(self):
        if self._thread is None:
            self.start()
        self._thread.join()

        # lambda has now been invoked and _invoke_response *should* be populated
        # TODO error handling, logs from the lambda, etc
        # moto returns None for payload in python 3.6
        if self._invoke_response["Payload"] is not None:
            payload = self._invoke_response["Payload"].read().decode("utf8")
        else:
            raise InvocationError("No invoke response, even though the AWS lambda function has been invoked.")
        self._logger.info("Got payload {payload} from thread {thread}".format(payload=payload, thread=self._thread))
        return json.loads(payload)


class AppProvider(Enum):
    AWS = 1


class ChiliPepper:
    def create_app(self, app_name, app_provider=AppProvider.AWS, config=Config()):
        # type: (str, AppProvider) -> App
        if app_provider == AppProvider.AWS:
            return AwsApp(app_name, config)
        else:
            raise ChiliPepperException("Unknown app provider {app_provider}".format(app_provider=app_provider))


class TaskFunction:
    def __init__(self, func, environment_variables=None):
        # type: (builtins.function, Optional[Dict]) -> None
        self._func = func
        self._environment_variables = environment_variables if environment_variables is not None else dict()

    @property
    def func(self):
        # type: () -> builtins.function
        return self._func

    @property
    def environment_variables(self):
        # type: () -> Dict
        return self._environment_variables

    def __eq__(self, other):
        # type: (TaskFunction) -> bool
        return type(other) == TaskFunction and self.func == other.func and self.environment_variables == other.environment_variables

    def __ne__(self, other):
        # type: (TaskFunction) -> bool
        # need to implement because of python2.7
        # https://docs.python.org/2.7/reference/datamodel.html#object.__ne__
        return not (self == other)


class App:
    def __init__(self, app_name, config=Config()):
        # type: (str, Config) -> None
        self._app_name = app_name
        self.conf = config
        self._logger = logging.getLogger(__name__)
        self._task_functions = list()

    @property
    def app_name(self):
        # type: () -> str
        return self._app_name

    @property
    def task_functions(self):
        # type: () -> List[TaskFunction]
        return self._task_functions

    def task(self):
        raise NotImplementedError()


class AwsApp(App):
    @property
    def bucket_name(self):
        # type: () -> str
        return self.conf["aws"]["bucket_name"]

    @property
    def runtime(self):
        # type: () -> str
        return self.conf["aws"]["runtime"]  # TODO should runtime be set by sys.version_info?

    def task(self, environment_variables=None):
        def _decorator(func,):
            # Ensure that the function signature matches what lambda expects
            # otherwise it will not be callabale from lambda
            # https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html
            # TODO make this cloud-agnostic
            try:
                function_signature = inspect.signature(func)
                function_parameter_list = list(function_signature.parameters.keys())
            except AttributeError:
                # python2.7 has different inspect module
                function_arg_spec = inspect.getargspec(func)
                function_parameter_list = list(function_arg_spec.args)
            if function_parameter_list != ["event", "context"]:
                raise InvalidFunctionSignature(
                    "Chili-pepper requires that you task functions has 2 parameters - 'event' and 'context' to match what Lambda expects. Your function "
                    + func.__module__
                    + "."
                    + func.__name__
                    + " has these parameters: "
                    + str(function_parameter_list)
                )

            self._task_functions.append(TaskFunction(func, environment_variables=environment_variables))

            def _delay_wrapper(event):
                # see https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html
                # the delay function arguments must be just the event argument
                # context is added by lambda
                """
                plan of attack
                1) Compute or look up the function name
                2) call https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke
                   in a separate thread (since invoke only gives you useful feedback if you call it synchronously)
                3) return a wrapper of the response, payload, logs, etc
                """
                # TODO make this cloud agnostic, abstracting it depending on the cloud provider
                deployer = Deployer(self)
                lambda_function_name = deployer.get_function_id(func)  # TODO alias/versioning support?
                result = Result(lambda_function_name, event)
                result.start()
                return result

            func.delay = _delay_wrapper
            return func

        return _decorator
