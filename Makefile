.PHONY: yapf flake8 test install-latest-local

install-latest-local:
	pip install -e .
	pip install -r requirements.txt

yapf:
	yapf --in-place --recursive --parallel --exclude=.tox/* .

flake8:
	flake8