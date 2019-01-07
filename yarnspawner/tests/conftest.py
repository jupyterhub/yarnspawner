import os
import subprocess
from contextlib import contextmanager

import pytest
import skein
from jupyterhub.tests.conftest import app, io_loop
from jupyterhub.tests.mocking import MockHub
from yarnspawner import YarnSpawner


MockHub.hub_ip = "edge.example.com"
MockHub.log_level = 'debug'


KEYTAB_PATH = "/home/testuser/testuser.keytab"
HAS_KERBEROS = os.path.exists(KEYTAB_PATH)


@pytest.fixture(scope="session")
def kinit():
    if HAS_KERBEROS:
        subprocess.check_call(["kinit", "-kt", KEYTAB_PATH, "testuser"])


@pytest.fixture(scope="session")
def security(tmpdir_factory):
    path = str(tmpdir_factory.mktemp('security'))
    return skein.Security.new_credentials().to_directory(path)


@pytest.fixture(scope="session")
def skein_client(security, kinit):
    with skein.Client(security=security) as skein_client:
        yield skein_client


@pytest.fixture(scope='session')
def conda_env():
    envpath = 'yarnspawner-test-env.tar.gz'
    if not os.path.exists(envpath):
        conda_pack = pytest.importorskip('conda_pack')
        conda_pack.pack(output=envpath, verbose=True)
    return envpath


@pytest.fixture(scope='module')
def configure_app(app, conda_env):
    app.tornado_settings['spawner_class'] = YarnSpawner
    c = app.config
    c.YarnSpawner.localize_files = {'environment': conda_env}
    c.YarnSpawner.prologue = ('set -x -e\n'
                              'source environment/bin/activate\n'
                              'env\n'
                              'ls\n')
    c.YarnSpawner.mem_limit = '512 M'
    if HAS_KERBEROS:
        c.YarnSpawner.principal = 'testuser'
        c.YarnSpawner.keytab = KEYTAB_PATH
    return app


def ensure_no_apps(skein_client, error=True):
    apps = skein_client.get_applications()
    if apps:
        for app in apps:
            skein_client.kill_application(app.id)
        if error:
            applist = '\n'.join('- %s' % a.id for a in apps)
            msg = ("Expected cluster to have no apps currently running.\n"
                   "Found:\n\n"
                   "{0}\n\n"
                   "Killed all applications").format(applist)
            raise AssertionError(msg)


@contextmanager
def clean_cluster(skein_client):
    ensure_no_apps(skein_client, error=False)
    try:
        yield
    finally:
        ensure_no_apps(skein_client, error=True)
