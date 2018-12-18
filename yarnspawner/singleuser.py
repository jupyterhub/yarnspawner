import os

from jupyterhub.singleuser import SingleUserNotebookApp
from jupyterhub.utils import random_port, url_path_join
from traitlets import default


# Borrowed and modified from jupyterhub/batchspawner:
# https://github.com/jupyterhub/batchspawner/blob/d1052385f2/batchspawner/singleuser.py
class YarnSingleUserNotebookApp(SingleUserNotebookApp):
    @default('port')
    def _port(self):
        return random_port()

    def start(self):
        self.hub_auth._api_request(method='POST',
                                   url=url_path_join(self.hub_api_url, 'yarnspawner'),
                                   json={'port': self.port})
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
