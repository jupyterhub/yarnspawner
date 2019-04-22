#!/usr/bin/env bash
set -x -e

if [[ "$DOCS" != "true" ]]; then
    sudo rm /usr/local/bin/docker-compose
    curl -L https://github.com/docker/compose/releases/download/1.19.0/docker-compose-`uname -s`-`uname -m` > docker-compose
    chmod +x docker-compose
    sudo mv docker-compose /usr/local/bin
    # Install the test cluster
    pip install git+https://github.com/jcrist/hadoop-test-cluster.git
    # Start the test cluster
    htcluster startup --mount .:yarnspawner --config $CLUSTER_CONFIG
fi
