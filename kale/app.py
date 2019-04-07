import builtins
import inspect

from kale.exception import KaleException

try:
    from typing import List
except ImportError:
    # python2.7 doesn't have typing, and I don't want to mess with mypy yet
    pass


class InvalidFunctionSignature(KaleException):
    pass


class Kale:
    def __init__(self, app_name, bucket_name, runtime):
        # type: (str, str, str) -> None
        self._app_name = app_name
        self._bucket_name = bucket_name
        self._runtime = runtime
        self._task_functions = list()
        self._function_handles = list()

    @property
    def app_name(self):
        # type: () -> str
        return self._app_name

    @property
    def bucket_name(self):
        # type: () -> str
        return self._bucket_name

    @property
    def runtime(self):
        # type: () -> str
        return self._runtime

    @property
    def function_handles(self):
        # type: () -> List[str]
        return self._function_handles

    @property
    def task_functions(self):
        # type: () -> List[builtins.function]
        return self._task_functions

    def task(self, func):
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
        if function_parameter_list != ['event', 'context']:
            raise InvalidFunctionSignature(
                "Kale requires that you task functions has 2 parameters - 'event' and 'context' to match what Lambda expects. Your function " +
                func.__module__ + '.' + func.__name__ + ' has these parameters: ' + str(function_parameter_list))

        self._task_functions.append(func)

        def _delay_wrapper(event):
            # see https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model-handler-types.html
            # the delay function arguments must be just the event argument
            # context is added by lambda
            '''
            plan of attack
            1) Compute or look up the function name
            2) call https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke
            3) return a wrapper of the response, payload, logs, etc

            The easy way would be to set InvocationType to Event, and look up the return value some other way...
            but the docs don't seem to explain how to do that.  AWS docs often are not very clear though.

            If the Event InvocationType don't work, we might need call invoke in a separate thread/process
            and return a generator that can wait until the synchronous call to lambda completes and returns everything.
            '''
            pass

        func.delay = _delay_wrapper
        return func
