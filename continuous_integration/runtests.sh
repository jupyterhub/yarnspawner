set -xe

cd yarnspawner
py.test yarnspawner --verbose
flake8 yarnspawner
