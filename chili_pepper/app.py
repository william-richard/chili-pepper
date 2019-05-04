import builtins
import inspect
import json
import logging
from copy import deepcopy
from enum import Enum
from threading import Thread

import boto3

from chili_pepper.config import Config
from chili_pepper.deployer import Deployer
from chili_pepper.exception import ChiliPepperException

try:
    from typing import List, Optional, Dict
except ImportError:
    # python2.7 doesn't have typing, and I don't want to mess with mypy yet
    pass


class InvalidFunctionSignature(ChiliPepperException):
    """Function Signature does not match required specifications

    Cloud providers require that functions have a specific signature.
    This exception is raised when a task does not match the required signature.

    """

    pass


class InvocationError(ChiliPepperException):
    """Raised when there was a problem invoking the serverless function
    """

    pass


class Result:
    """Task result object

    Result wraps the information returned when the serverless function is invoked.

    """

    def __init__(self, lambda_function_name, event):
        # type: (str, dict) -> None
        """
        Args:
            lambda_function_name: The name of the invoked AWS Lambda function
            event: The event dictionary to pass to the AWS Lambda function
        """
        self._logger = logging.getLogger(__name__)

        self._lambda_function_name = lambda_function_name
        self._event = event

        self._thread = None
        self._invoke_response = None

    def start(self):
        """Start executing the serverless function

        Invokes the serverless function.

        For AWS, this invokes the Lambda in a thread, since the only way to get results is to call syncronously.
        By putting the invoke call in a therad, it will not block the main application thread.

        Returns:
            Thread: The thread running the lambda
        """
        if self._thread is None:

            def lambda_run():
                lambda_client = boto3.client("lambda")
                self._invoke_response = lambda_client.invoke(FunctionName=self._lambda_function_name, Payload=json.dumps(self._event))
                return

            self._thread = Thread(target=lambda_run)
            self._thread.start()
        return self._thread

    def get(self):
        """Get the response from the serverless execution.

        This is a potentially blocking call.

        It will retrieve the return payload from the serverless function.  If it is called before the serverless function has finished,
        ``get`` will block until the serverless function returns.

        Raises:
            InvocationError: Raises if something goes retrieving the return payload of the serverless function.

        Returns:
            dict: The return payload of the serverless function
        """

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
    """Enum to identify the serverless provider.

    Currently unused.

    """

    AWS = 1


class ChiliPepper:
    def create_app(self, app_name, app_provider=AppProvider.AWS, config=None):
        # type: (str, AppProvider, Optional[Config]) -> App
        """[summary]

        Args:
            app_name ([type]): [description]
            app_provider ([type], optional): [description]. Defaults to AppProvider.AWS.
            config ([type], optional): [description]. Defaults to None.

        Raises:
            ChiliPepperException: [description]

        Returns:
            [type]: [description]
        """
        if config is None:
            config = Config()
        if app_provider == AppProvider.AWS:
            return AwsApp(app_name, config)
        else:
            raise ChiliPepperException("Unknown app provider {app_provider}".format(app_provider=app_provider))


class TaskFunction:
    """A wrapper around python functions that can be serverlessly deployed and executed by chili-pepper
    """

    def __init__(self, func, environment_variables=None):
        # type: (builtins.function, Optional[Dict]) -> None
        """
        Args:
            func (builtins.function): The python function object
            environment_variables (dict, optional): Environment variables that will be passed to the serverles function. Defaults to None.
        """
        self._func = func
        self._environment_variables = environment_variables if environment_variables is not None else dict()

    @property
    def func(self):
        # type: () -> builtins.function
        """
        Returns:
            builtins.function: The python function
        """
        return self._func

    @property
    def environment_variables(self):
        # type: () -> Dict
        """
        Returns:
            dict: The environment variable overrides for this function
        """
        return self._environment_variables

    def __eq__(self, other):
        # type: (TaskFunction) -> bool
        return (
            hasattr(other, "func")
            and self.func == other.func
            and hasattr(other, "environment_variables")
            and self.environment_variables == other.environment_variables
        )

    def __ne__(self, other):
        # type: (TaskFunction) -> bool
        # need to implement because of python2.7
        # https://docs.python.org/2.7/reference/datamodel.html#object.__ne__
        return not (self == other)

    def __str__(self):
        # type: () -> str
        # TODO unhardcode the class name
        return "TaskFunction {my_module}.{my_func_name}".format(my_module=self._func.__module__, my_func_name=self.func.__name__)


class App:
    """Cloud-agnostic App class

    App is the main class for applications that use Chili-Pepper.

    """

    def __init__(self, app_name, config=None):
        # type: (str, Optional[Config]) -> None
        """
        Args:
            app_name: The application name
            config: Optional default config object
        """
        if config is None:
            config = Config()

        self._app_name = app_name
        self.conf = config
        self._logger = logging.getLogger(__name__)
        self._task_functions = list()

    @property
    def app_name(self):
        # type: () -> str
        """
        The application name.
        """
        return self._app_name

    @property
    def task_functions(self):
        # type: () -> List[TaskFunction]
        """
        The task functions identified with the ``@app.task`` decorator
        """
        return self._task_functions

    def task(self, environment_variables=None):
        # type: (Optional[Dict]) -> builtins.func
        """
        The decorator to denote tasks.  It must be implemented by cloud-specific App child classes.

        Args:
            environment_variables: Environment variables to apply to the task
        """
        raise NotImplementedError()


class AwsApp(App):
    @property
    def bucket_name(self):
        # type: () -> str
        """
        The AWS S3 bucket name that holds the lambda deployment packages
        """
        return self.conf["aws"]["bucket_name"]

    @property
    def runtime(self):
        # type: () -> str
        """
        The AWS lambda runtime identifier.

        .. _AWS lambda runtime documentation:
            https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
        """
        return self.conf["aws"]["runtime"]  # TODO should runtime be set by sys.version_info?

    def task(self, environment_variables=None):
        # type: (Optional[Dict]) -> builtins.func

        if environment_variables is None:
            environment_variables = dict()

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

            # combine the default and default env vars
            task_environment_variables = deepcopy(self.conf["default_environment_variables"])
            task_environment_variables.update(environment_variables)

            self._task_functions.append(TaskFunction(func, environment_variables=task_environment_variables))

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
