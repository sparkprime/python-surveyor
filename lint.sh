#!/bin/bash
# Lint the python_surveyor package and tests with pylint and pyright.

DIRS="./python_surveyor ./tests"

pylint $DIRS
pyright $DIRS
