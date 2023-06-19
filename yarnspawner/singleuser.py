import json
import os

from jupyter_server.serverapp import ServerApp
from jupyterhub.utils import random_port, url_path_join
from traitlets import default

if not os.environ.get("JUPYTERHUB_SINGLEUSER_APP"):
    # setting this env prior to import of jupyterhub.singleuser avoids unnecessary import of notebook
    os.environ["JUPYTERHUB_SINGLEUSER_APP"] = "jupyter_server.serverapp.ServerApp"

from jupyterhub.singleuser.mixins import make_singleuser_app

SingleUserServerApp = make_singleuser_app(ServerApp)


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d1052385f2/batchspawner/singleuser.py
class YarnSingleUserNotebookApp(SingleUserServerApp):
    @default('port')
    def _port(self):
        return random_port()

    def start(self):
        self.io_loop.add_callback(self.hub_auth._api_request, method='POST',
                                  url=url_path_join(self.hub_api_url, 'yarnspawner'),
                                  body=json.dumps({'port': self.port}))
        super().start()


def main(argv=None):
    # Set configuration directory to something local if not already set
    for var in ['JUPYTER_RUNTIME_DIR', 'JUPYTER_DATA_DIR']:
        if os.environ.get(var) is None:
            if not os.path.exists('.jupyter'):
                os.mkdir('.jupyter')
            os.environ[var] = './.jupyter'
    return YarnSingleUserNotebookApp.launch_instance(argv)


if __name__ == "__main__":
    main()
