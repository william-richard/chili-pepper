.PHONY: yapf flake8 test install-latest-local clean

install-latest-local:
	pip install -e .
	pip install -r requirements.txt

lint:
	yapf --in-place --recursive --parallel --exclude=.tox/* .
	unify --recursive --in-place .
	flake8

clean:
	find . -name '__pycache__' -delete -print -o -name '*.pyc' -delete -print
