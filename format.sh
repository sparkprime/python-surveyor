#!/bin/bash
# Format the python_surveyor package and tests.
# Runs isort then black (the project's invariant is that this is a no-op on
# already-formatted code).

DIRS="./python_surveyor ./tests"

isort $DIRS
black $DIRS
