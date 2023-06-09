import os
import sys
from runpy import run_path
from shutil import which

import requests
from jupyterhub.utils import random_port, url_path_join
from jupyterhub.services.auth import HubAuth


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d5f9a0bbaa92748267bb1dd2cc4d4a0436670482/batchspawner/singleuser.py
def main(argv=None):
    # Set configuration directory to something local if not already set
    for var in ['JUPYTER_RUNTIME_DIR', 'JUPYTER_DATA_DIR']:
        if os.environ.get(var) is None:
            if not os.path.exists('.jupyter'):
                os.mkdir('.jupyter')
            os.environ[var] = './.jupyter'

    port = random_port()
    hub_auth = HubAuth()
    hub_auth.client_ca = os.environ.get("JUPYTERHUB_SSL_CLIENT_CA", "")
    hub_auth.certfile = os.environ.get("JUPYTERHUB_SSL_CERTFILE", "")
    hub_auth.keyfile = os.environ.get("JUPYTERHUB_SSL_KEYFILE", "")

    url = url_path_join(hub_auth.api_url, "yarnspawner")

    # internal_ssl kwargs
    kwargs = {}
    if hub_auth.certfile and hub_auth.keyfile:
        kwargs["cert"] = (hub_auth.certfile, hub_auth.keyfile)
    if hub_auth.client_ca:
        kwargs["verify"] = hub_auth.client_ca

    requests.post(
        url,
        headers={"Authorization": f"token {hub_auth.api_token}"},
        json={"port": port},
        **kwargs,
    )

    cmd_path = which(sys.argv[1])
    sys.argv = sys.argv[1:] + ["--port={}".format(port)]
    run_path(cmd_path, run_name="__main__")


if __name__ == "__main__":
    main()