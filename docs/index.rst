.. chili-pepper documentation master file, created by
   sphinx-quickstart on Sat May  4 07:54:07 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

****************************************
Welcome to chili-pepper's documentation!
****************************************

.. toctree::
   :maxdepth: 2
   :caption: Contents:

**Asynchronous Serverless Task Execution**

Chili-Pepper is a simple framework that makes it easy to execute
tasks without interrupting the main flow of your application.
It handles serverless deployment and task execution.
It allows you to run important functions in parallel with
your main application without managing
any additional infrastructure, like servers or queues.

Command
=======

.. code-block:: bash

    usage: chili [-h] [--app APP] {deploy} ...

    Serverless asynchronous tasks

    positional arguments:
    {deploy}           Chili-Pepper commands
        deploy           Deploy functions to serverless provider

    optional arguments:
    -h, --help         show this help message and exit
    --app APP, -A APP  The Chili-Pepper application location


Getting Started
===============

Installing Chili-Pepper
-----------------------

.. code-block:: bash

    pip install chili-pepper

Serverless Provider
-------------------

Next, you need to configure your serverless provider credentials.

Amazon Web Services (AWS)
^^^^^^^^^^^^^^^^^^^^^^^^^

You can provide AWS credentials in many ways, including environment variables, your aws credentials file, or a server role.  See [the boto3 documentation about credential configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials) for details.

These credentials need to be allowed to create, execute and delete
AWS Lambda functions and IAM roles.

You will also need an S3 bucket (with versioning enabled).

Azure
^^^^^

Microsoft Azure Cloud is not supported at this time,
but there are plans to support it in the future.

Google Cloud
^^^^^^^^^^^^

Google Cloud is not supported at this time,
but there are plans to support it in the future.

Creating the Chili-Pepper App
-----------------------------

The Chili-Pepper app will be used to identify and deploy your functions
to the serverless cloud provider.

.. code-block:: python

    app = ChiliPepper(app_name="demo")


Of course, the ``app`` variable can have any name -
we'll be calling it ``app`` in these examples.

AWS Configuration
^^^^^^^^^^^^^^^^^

You need to pass some AWS specific configs to the app.

Bucket
""""""

.. code-block:: python

    app.conf["aws"]["bucket_name"] = "my-chili-pepper-bucket"

This bucket will be used for storing AWS Lambda deployment packages.
You should enable versioning on the bucket.

Runtime
"""""""

.. code-block:: python

    app.conf["aws"]["runtime"] = "python3.7"

AWS Lambda supports several python runtimes.  See [the lambda runtime documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html) for a full list.  You must pass the "Identifier" for the runtime of your choice to the Chili-Pepper app config.

Creating a Task
---------------

You can use the Chili-Pepper app to identify tasks that should be run.

.. code-block:: python

    @app.task()
    def my_task(event, context):
        return f"Hello {event['name']}!"

Deploying
---------

Before you can asynchronously call your task,
you must deploy it to your cloud provider.

.. code-block:: bash

    chili deploy --app my_module.tasks.app

AWS Deployment
^^^^^^^^^^^^^^

Calling deploy will create a zipfile containing your code
as well as any python dependencies.
Chili-Pepper will then use upload that zipfile to your S3 bucket,
and use Cloudformation to create an AWS Lambda function
for each of the tasks you identified with the `app.task()` decorator.

Calling your task
-----------------

Now that you've deployed your tasks to the cloud,
you can call them asynchronously.

.. code-block:: python

    task_result = my_task.delay({"name": "Jalapeno"})
    print(task_result.get())

This will print ``Hello Jalapeno!``,
after executing `my_task` in a serverless function.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
