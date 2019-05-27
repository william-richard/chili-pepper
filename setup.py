import os
import subprocess
import re

import setuptools

"""
taken from
http://blogs.nopcode.org/brainstorm/2013/05/20/pragmatic-python-versioning-via-setuptools-and-git-tags/
Fetch version from git tags, and write to version.py.
Also, when git is not available (PyPi package), use stored version.py.
"""
version_py = os.path.join(os.path.dirname(__file__), "version.py")

try:
    version_git = subprocess.check_output(["git", "describe", "--tags"]).decode().rstrip()
    # this will result in 2 possible answers
    # An exact tag (0.0.1) or relative to an exact tag (0.0.1-2-abc123)
    # The 2nd case (0.0.1-2-abc123) is not considered valid by https://www.python.org/dev/peps/pep-0440/
    # so adjust it to create a dev release tag.  This won't be unique, but we should only be pushing to
    # test pypi when a merge to master happens, so it should work out
    if "-" in version_git:
        split_version_git = version_git.split("-")
        version_git = split_version_git[0] + ".dev" + split_version_git[1]
except Exception:
    with open(version_py, "r") as fh:
        version_git = fh.read().strip().split("=")[-1].replace('"', "")

version_msg = "# Do not edit this file, pipeline versioning is governed by git tags"
with open(version_py, "w") as fh:
    fh.write(version_msg + os.linesep + '__version__ = "' + str(version_git) + '"' + os.linesep)


# http://martin.majlis.cz/integrating-github-with-pypi-travis-ci-readthedocs-and-code-climate/
def fix_doc(txt):
    return re.sub(r"\.\. PYPI-BEGIN([\r\n]|.)*?PYPI-END", "", txt, re.DOTALL)


# see https://packaging.python.org/guides/making-a-pypi-friendly-readme/
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, "README.rst"), encoding="utf-8") as f:
        long_description = f.read()
except TypeError:
    # python 2.7 is old and dumb
    # 'encoding' is an invalid keyword argument for this function
    with open(os.path.join(this_directory, "README.rst"), "r") as f:
        long_description = f.read()

long_description = fix_doc(long_description)

setuptools.setup(
    name="chili_pepper",
    version="{ver}".format(ver=version_git),
    author="William Richard",
    author_email="william.richard.no.s@gmail.com",
    description="Serverless asynchronous task execution",
    long_description_content_type="text/x-rst",
    long_description=long_description,
    license="Apache 2.0",
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": ["chili = chili_pepper.main:main"]},
    install_requires=["awacs", "boto3", "pathlib2", "troposphere"],
    python_requires=">=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, <4",
    url="https://gitlab.com/william-richard/chili-pepper",
    project_urls={
        "Source": "https://gitlab.com/william-richard/chili-pepper",
        "Documentation ": "https://chili-pepper.readthedocs.io/en/stable/",
        "Support": "https://www.patreon.com/chili_pepper",
    },
    keywords="cloud serverless task job queue distributed",
    classifiers=[
        "Development Status :: 1 - Planning",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python",
        "Topic :: System :: Distributed Computing",
    ],
)
