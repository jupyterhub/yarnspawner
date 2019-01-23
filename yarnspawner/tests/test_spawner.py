import pytest
from unittest.mock import Mock

from jupyterhub.tests.test_api import add_user, api_request
from jupyterhub.tests.mocking import public_url
from jupyterhub.tests.utils import async_requests
from jupyterhub.utils import url_path_join
from jupyterhub.objects import Hub, Server
from tornado import gen

import skein
from yarnspawner import YarnSpawner
from .conftest import clean_cluster, assert_shutdown_in


@pytest.mark.gen_test(timeout=60)
def test_integration(skein_client, app, configure_app):
    with clean_cluster(skein_client):
        # Create a user
        add_user(app.db, app, name="alice")
        alice = app.users["alice"]
        assert isinstance(alice.spawner, YarnSpawner)
        token = alice.new_api_token()

        # Not started, status should be 0
        status = yield alice.spawner.poll()
        assert status == 0

        # Stop can be called before start, no-op
        yield alice.spawner.stop()

        # Start the server, and wait for it to start
        resp = None
        while resp is None or resp.status_code == 202:
            yield gen.sleep(2.0)
            resp = yield api_request(app, "users", "alice", "server", method="post")

        # Check that everything is running fine
        url = url_path_join(public_url(app, alice), "api/status")
        resp = yield async_requests.get(
            url, headers={'Authorization': 'token %s' % token}
        )
        resp.raise_for_status()
        assert "kernels" in resp.json()

        # Save the app_id to use later
        app_id = alice.spawner.app_id

        # Shutdown the server
        resp = yield api_request(app, "users", "alice", "server", method="delete")
        resp.raise_for_status()
        assert_shutdown_in(skein_client, app_id, timeout=10)

        # Check status
        status = yield alice.spawner.poll()
        assert status == 0


class MockUser(Mock):
    name = 'myname'
    server = Server()

    @property
    def url(self):
        return self.server.url


def test_specification():
    spawner = YarnSpawner(hub=Hub(), user=MockUser())

    spawner.queue = 'myqueue'
    spawner.prologue = 'Do this first'
    spawner.epilogue = 'Do this after'
    spawner.mem_limit = '1 G'
    spawner.cpu_limit = 2
    spawner.localize_files = {
        'environment': 'environment.tar.gz',
        'file2': {'source': 'path/to/file',
                  'visibility': 'public'}
    }
    spawner.env = {'TEST_ENV_VAR': 'TEST_VALUE'}

    spec = spawner._build_specification()

    assert spec.user == 'myname'
    assert spec.queue == 'myqueue'

    assert 'Do this first\n' in spec.master.script
    assert 'python -m yarnspawner.singleuser' in spec.master.script
    assert 'Do this after' in spec.master.script

    assert spec.master.resources == skein.Resources(memory='1 GiB', vcores=2)

    assert 'environment' in spec.master.files
    assert 'file2' in spec.master.files
    assert spec.master.files['file2'].visibility == 'public'

    assert 'TEST_ENV_VAR' in spec.master.env
    assert 'JUPYTERHUB_API_TOKEN' in spec.master.env
