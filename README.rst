.. chili-pepper documentation master file, created by
   sphinx-quickstart on Sat May  4 07:54:07 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

****************************************
chili-pepper
****************************************

**Asynchronous Serverless Task Execution**

Chili-Pepper is a simple framework that makes it easy to execute
tasks without interrupting the main flow of your application.
It handles serverless deployment and task execution.
It allows you to run important functions in parallel with
your main application with
**zero downtime, zero maintenance and infinite scaling**.


.. image:: https://badge.fury.io/py/chili-pepper.svg
    :target: https://badge.fury.io/py/chili-pepper

.. image:: https://readthedocs.org/projects/chili-pepper/badge/?version=latest
    :target: https://chili-pepper.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/pypi/l/chili-pepper.svg
    :alt: PyPI - License

.. image:: https://img.shields.io/pypi/pyversions/chili-pepper.svg
    :alt: PyPI - Python Version

|

.. image:: https://gitlab.com/william-richard/chili-pepper/badges/master/pipeline.svg
    :target: https://gitlab.com/william-richard/chili-pepper/commits/master
    :alt: Pipeline Status

.. image:: https://gitlab.com/william-richard/chili-pepper/badges/master/coverage.svg
    :target: https://gitlab.com/william-richard/chili-pepper/commits/master
    :alt: Coverage report

.. image:: https://img.shields.io/librariesio/release/pypi/chili-pepper.svg
    :alt: Libraries.io dependency status for latest release

|

.. image:: https://c5.patreon.com/external/logo/become_a_patron_button.png
    :alt: Become a Supporter of Chili-Pepper
    :target: https://www.patreon.com/chili_pepper
    :height: 30px

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

You can provide AWS credentials in many ways, including environment variables, your aws credentials file, or a server role.  See `the boto3 documentation about credential configuration <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials>`_ for details.

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

You need to pass these required AWS specific configs to the app.
For a full list of AWS configuration options, see `Aws Configuration <https://chili-pepper.readthedocs.io/en/stable/config.html#aws-configuration>`_.

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

AWS Lambda supports several python runtimes.  See `the lambda runtime documentation <https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html>`_ for a full list.  You must pass the "Identifier" for the runtime of your choice to the Chili-Pepper app config.

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

Support
=======

Chili-Pepper is built by a 1 person team supported by
`these awesome backers, supporters and sponsors <https://gitlab.com/william-richard/chili-pepper/blob/master/BACKERS.rst>`_.
If you use Chili-Pepper, I would love to hear from you!
And, if I have earned your support, please consider backing me `on Patreon <https://www.patreon.com/chili_pepper>`_.

.. image:: https://c5.patreon.com/external/logo/become_a_patron_button.png
    :alt: Become a Supporter of Chili-Pepper
    :target: https://www.patreon.com/chili_pepper
    :height: 40px

.. PYPI-BEGIN

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   config
   API Docs <modules>
   backers
   license


.. PYPI-END
