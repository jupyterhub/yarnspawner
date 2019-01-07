import pytest

from jupyterhub.tests.test_api import add_user, api_request
from jupyterhub.tests.mocking import public_url
from jupyterhub.tests.utils import async_requests
from jupyterhub.utils import url_path_join

from yarnspawner import YarnSpawner
from .conftest import clean_cluster


def intercept(method):
    def inner(*args, **kwargs):
        import pdb;pdb.set_trace
        method(*args, **kwargs)
    return inner


@pytest.mark.asyncio
async def test_basic(skein_client, app, configure_app):
    with clean_cluster(skein_client):
        add_user(app.db, app, name="alice")
        alice = app.users["alice"]
        alice._new_spawner = intercept(alice._new_spawner)
        assert isinstance(alice.spawner, YarnSpawner)
        token = alice.new_api_token()
        # start the server
        resp = None
        while resp is None or resp.status_code == 202:
            resp = await api_request(app, "users", "alice", "server", method="post")
        assert resp.status_code == 201, resp.text

        url = url_path_join(public_url(app, alice), "api/status")
        resp = await async_requests.get(url, headers={'Authorization': 'token %s' % token})
        assert resp.url == url
        resp.raise_for_status()
        assert "kernels" in resp.json()
