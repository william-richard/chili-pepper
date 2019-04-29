.PHONY: flake8 test install-latest-local clean dev-osx

DOCKER := $(shell command -v docker 2> /dev/null)
AZURE_FUNC := $(shell command -v func 2> /dev/null)

test-dependencies: install-latest-local
ifndef DOCKER
    $(error "docker is not available - please see www.docker.com/get-started for install instructions")
endif
ifndef AZURE_FUNC
    $(error "Azure Function Core Tools are not available - please see docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools for install instructions")
endif

install-latest-local:
	pip install  --no-use-pep517 -e .
	pip install -r requirements.txt

lint:
	black .
	flake8

clean:
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print -o  -name '*.pyo' -delete -print
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

