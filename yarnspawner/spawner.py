import skein
from jupyterhub.spawner import Spawner
from jupyterhub.traitlets import Command, ByteSpecification
from traitlets import Unicode, Dict, Integer
from tornado import gen


_STOPPED_STATES = {'FAILED', 'KILLED', 'FINISHED'}


class YarnSpawner(Spawner):
    """A spawner for starting singleuser instances in a YARN container."""

    start_timeout = Integer(
        300,
        help="Timeout (in seconds) before giving up on starting of singleuser server.",
        config=True
    )

    ip = Unicode(
        "0.0.0.0",
        help="The IP address (or hostname) the singleuser server should listen on.",
        config=True
    )

    principal = Unicode(
        None,
        help='Kerberos principal for JupyterHub user',
        allow_none=True,
        config=True,
    )

    keytab = Unicode(
        None,
        help='Path to kerberos keytab for JupyterHub user',
        allow_none=True,
        config=True,
    )

    queue = Unicode(
        'default',
        help='The YARN queue to submit applications under',
        config=True,
    )

    localize_files = Dict(
        help="""
        Extra files to distribute to the singleuser server container.

        This is a mapping from ``local-name`` to ``resource``. Resource paths
        can be local, or in HDFS (prefix with ``hdfs://...`` if so). If an
        archive (``.tar.gz`` or ``.zip``), the resource will be unarchived as
        directory ``local-name``. For finer control, resources can also be
        specified as ``skein.File`` objects, or their ``dict`` equivalents.

        This can be used to distribute conda/virtual environments by
        configuring the following:

        .. code::

            c.YarnSpawner.localize_files = {
                'environment': {
                    'source': 'hdfs:///path/to/archived/environment.tar.gz',
                    'visibility': 'public'
                }
            }
            c.YarnSpawner.prologue = 'source environment/bin/activate'

        These archives are usually created using either ``conda-pack`` or
        ``venv-pack``. For more information on distributing files, see
        https://jcrist.github.io/skein/distributing-files.html.
        """,
        config=True,
    )

    prologue = Unicode(
        '',
        help='Script to run before singleuser server starts.',
        config=True,
    )

    cmd = Command(
        ['python -m yarnspawner.singleuser'],
        allow_none=True,
        help='The command used for starting the singleuser server.',
        config=True
    )

    mem_limit = ByteSpecification(
        '2 G',
        help="""
        Maximum number of bytes a singleuser notebook server is allowed to
        use. Allows the following suffixes:

        - K -> Kibibytes
        - M -> Mebibytes
        - G -> Gibibytes
        - T -> Tebibytes
        """,
        config=True)

    cpu_limit = Integer(
        1,
        min=1,
        help="""
        Maximum number of cpu-cores a singleuser notebook server is allowed to
        use. Unlike other spawners, this must be an integer amount >= 1.
        """,
        config=True)

    epilogue = Unicode(
        '',
        help='Script to run after singleuser server ends.',
        config=True,
    )

    script_template = Unicode(
        ("{prologue}\n"
         "{singleuser_command}\n"
         "{epilogue}"),
        help="""
        Template for application script.

        Filled in by calling ``script_template.format(**variables)``. Variables
        include the following attributes of this class:

        - prologue
        - singleuser_command
        - epilogue
        """,
        config=True,
    )

    # A cache of clients by (principal, keytab). In most cases this will only
    # be a single client. These should persist for the lifetime of jupyterhub.
    clients = {}

    async def _get_client(self):
        key = (self.principal, self.keytab)
        client = type(self).clients.get(key)
        if client is None:
            kwargs = dict(principal=self.principal,
                          keytab=self.keytab,
                          security=skein.Security.new_credentials())
            client = await gen.IOLoop.current().run_in_executor(
                None, lambda: skein.Client(**kwargs)
            )
            type(self).clients[key] = client
        return client

    @property
    def singleuser_command(self):
        """The full command (with args) to launch a singleuser server"""
        return ' '.join(self.cmd + self.get_args())

    def _build_specification(self):
        script = self.script_template.format(
            prologue=self.prologue,
            singleuser_command=self.singleuser_command,
            epilogue=self.epilogue
        )

        resources = skein.Resources(
            memory='%d b' % self.mem_limit,
            vcores=self.cpu_limit
        )

        security = skein.Security.new_credentials()

        # Support dicts as well as File objects
        files = {k: skein.File.from_dict(v) if isinstance(v, dict) else v
                 for k, v in self.localize_files.items()}

        master = skein.Master(
            resources=resources,
            files=files,
            env=self.get_env(),
            script=script,
            security=security
        )

        return skein.ApplicationSpec(
            name='jupyterhub',
            queue=self.queue,
            user=self.user.name,
            master=master
        )

    def load_state(self, state):
        super().load_state(state)
        self.app_id = state.get('app_id', '')

    def get_state(self):
        state = super().get_state()
        if self.app_id:
            state['app_id'] = self.app_id
        return state

    def clear_state(self):
        super().clear_state()
        self.app_id = ''

    async def start(self):
        loop = gen.IOLoop.current()

        spec = self._build_specification()

        client = await self._get_client()
        # Set app_id == 'PENDING' to signal that we're starting
        self.app_id = 'PENDING'
        try:
            self.app_id = app_id = await loop.run_in_executor(None, client.submit, spec)
        except Exception as exc:
            # We errored, no longer pending
            self.app_id = ''
            self.log.error(
                "Failed to submit application for user %s. Original exception:",
                self.user.name,
                exc_info=exc
            )
            raise

        # Wait for application to start
        while True:
            report = await loop.run_in_executor(
                None, client.application_report, app_id
            )
            state = str(report.state)
            if state in _STOPPED_STATES:
                raise Exception("Application %s failed to start, check "
                                "application logs for more information"
                                % app_id)
            elif state == 'RUNNING':
                self.current_ip = report.host
                break
            else:
                await gen.sleep(0.5)

        # Wait for port to be set
        while getattr(self, 'current_port', 0) == 0:
            await gen.sleep(0.5)

            report = await loop.run_in_executor(
                None, client.application_report, app_id
            )
            if str(report.state) in _STOPPED_STATES:
                raise Exception("Application %s failed to start, check "
                                "application logs for more information"
                                % app_id)

        return self.current_ip, self.current_port

    async def poll(self):
        if self.app_id == '':
            return 0
        elif self.app_id == 'PENDING':
            return None

        client = await self._get_client()
        report = await gen.IOLoop.current().run_in_executor(
            None, client.application_report, self.app_id
        )
        status = str(report.final_status)
        if status in {'SUCCEEDED', 'KILLED'}:
            return 0
        elif status == 'FAILED':
            return 1
        else:
            return None

    async def stop(self, now=False):
        if self.app_id == 'PENDING':
            # The application is in the process of being submitted. Wait for a
            # reasonable amount of time until we have an application id
            for i in range(20):
                if self.app_id != 'PENDING':
                    break
                await gen.sleep(0.1)
            else:
                self.log.warn("Application has been PENDING for an "
                              "unreasonable amount of time, there's likely "
                              "something wrong")

        # Application not submitted, or submission errored out, nothing to do.
        if self.app_id == '':
            return

        client = await self._get_client()
        await gen.IOLoop.current().run_in_executor(
            None, client.kill_application, self.app_id
        )
