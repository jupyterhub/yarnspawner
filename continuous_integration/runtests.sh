#!/usr/bin/env bash
set -xe

cd yarnspawner
py.test yarnspawner --verbose
flake8 yarnspawner
