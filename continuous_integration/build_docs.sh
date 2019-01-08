#!/usr/bin/env bash
set -x -e

# Build docs
pushd docs
make html
popd

# Maybe deploy documentation
if [[ "$TRAVIS_BRANCH" == "master" && "$TRAVIS_EVENT_TYPE" == "push" ]]; then
    doctr deploy . --built-docs docs/build/html/
fi
