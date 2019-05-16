#############
Configuration
#############

This document describes the configuration options available.
These are set on the :py:class:`chili_pepper.config.Config` object when
initializing an :py:class:`chili_pepper.app.App` object,
or by modifying ``app.conf``.

General Configuration
---------------------

``default_environment_variables``
"""""""""""""""""""""""""""""""""

Default: :const:`None`.

A dictionary of environment variables
that should be set in all serverless functions.

These values can be augmented by passing the ``environment_variables``
argument to :py:meth:`chili_pepper.app.App.task` decorator.

.. _aws-configuration:

AWS Configuration
-----------------

All AWS configuration lives under the ``aws`` namespace.

For example ``config["aws"]["bucket_name"]``

``bucket_name``
"""""""""""""""

*required*

Chili_pepper will use this bucket for storing AWS Lambda deployment packages.
You should enable versioning on the bucket.
You also must ensure that the user or role deploying chili_pepper
is allowed to put objects in this bucket.

``runtime``
"""""""""""

*required*

The AWS Lambda python runtime to use.
Several python runtimes are supported -
see `the lambda runtime documentation <https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html>`_ for a full list.
You must pass the "Identifier" for the runtime of
your choice to the Chili-Pepper app config.

``kms_key``
"""""""""""

Default: :const:`None`.

Pass a KMS key arn to use that key to encrypt any
AWS Lambda environment variables.
Chili pepper will also automatically grant the
lambda functions ``kms:Decrypt`` permissions to this key.

``default_tags``
""""""""""""""""

Default: :const:`None`.

A ``dict`` of tags to apply to all
resources deployed with chili_pepper.

These values can be augmented by passing the ``tags``
argument to :py:meth:`chili_pepper.app.AwsApp.task` decorator.


``extra_allow_permissions``
"""""""""""""""""""""""""""

Default: :const:`None`.

A list of :py:class:`chili_pepper.app.AwsAllowPermission` objects,
defining extra permissions to grant to the lambda functions.

``chili_pepper`` always grants access to `arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole <https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html>`_.
