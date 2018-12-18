import skein
from jupyterhub.spawner import Spawner
from jupyterhub.traitlets import Command, ByteSpecification
from traitlets import Unicode, Dict, Integer
from tornado import gen


class YarnSpawner(Spawner):
    """A spawner for starting single-user instances in a YARN container."""

    start_timeout = Integer(
        300,
        help="Timeout (in seconds) before giving up on starting of single-user server.",
        config=True
    )

    ip = Unicode(
        "0.0.0.0",
        help="The IP address (or hostname) the single-user server should listen on.",
        config=True
    )

    principal = Unicode(
        '',
        help='Kerberos principal for JupyterHub user',
        config=True,
    )

    keytab = Unicode(
        '',
        help='Path to kerberos keytab for JupyterHub user',
        config=True,
    )

    queue = Unicode(
        'default',
        help='The YARN queue to submit applications under',
        config=True,
    )

    localize_files = Dict(
        help="""
        Extra files to distribute to the single-user server container.

        This is a mapping from ``local-name`` to ``resource-path``. Resource
        paths can be local, or in HDFS (prefix with ``hdfs://...`` if so). If
        an archive (``.tar.gz`` or ``.zip``), the resource will be unarchived
        as directory ``local-name``.

        This can be used to distribute conda/virtual environments by
        configuring the following:

            c.YarnSpawner.localize_files = {
                'environment': '/path/to/archived/environment.tar.gz'
            }
            c.YarnSpawner.prologue = 'source environment/bin/activate'

        These archives are usually created using either ``conda-pack`` or
        ``venv-pack``.
        """,
        config=True,
    )

    prologue = Unicode(
        '',
        help='Script to run before single-user server starts.',
        config=True,
    )

    cmd = Command(['yarnspawner-singleuser'], allow_none=True, config=True)

    mem_limit = ByteSpecification(
        '2 G',
        help="""
        Maximum number of bytes a single-user notebook server is allowed to
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
        Maximum number of cpu-cores a single-user notebook server is allowed to
        use. Unlike other spawners, this must be an integer amount >= 1.
        """,
        config=True)

    epilogue = Unicode(
        '',
        help='Script to run after single-user server ends.',
        config=True,
    )

    script_template = Unicode(
        ("{prologue}\n",
         "{single_user_command}\n",
         "{epilogue}"),
        help="""
        Template for application script.

        Filled in by calling ``script_template.format(**variables)``. Variables
        include the following attributes of this class:
        - prologue
        - single_user_command
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
    def single_user_command(self):
        """The full command (with args) to launch a single-user server"""
        return ' '.join(self.cmd, + self.get_args())

    def _build_specification(self):
        script = self.script_template.format(
            prologue=self.prologue,
            cmd=self.single_user_command,
            epilogue=self.epilogue
        )

        resources = skein.Resources(
            memory='%d b' % self.mem_limit,
            vcores=self.cpu_limit
        )

        security = skein.Security.new_credentials()

        service = skein.Service(
            instances=1,
            resources=resources,
            files=self.localize_files,
            env=self.get_env(),
            commands=[script]
        )

        return skein.ApplicationSpec(
            name='jupyterhub',
            queue=self.queue,
            user=self.user.name,
            master=skein.Master(security=security),
            services={'jupyterhub': service}
        )

    def load_state(self, state):
        super().load_state(state)
        self.app_id = state.get('app_id', '')

    def get_state(self):
        state = super().get_state()
        if self.app_id:
            state.app_id = self.app_id
        return state

    def clear_state(self):
        super().clear_state()
        self.app_id = ''

    async def start(self):
        loop = gen.IOLoop.current()

        spec = self._build_specification()
        # Set app_id == 'PENDING' to signal `poll` that we're starting
        self.app_id = 'PENDING'

        client = await self._get_client()
        app_id = await loop.run_in_executor(None, client.submit, spec)
        self.app_id = app_id

        # Wait for application to start
        while True:
            report = await loop.run_in_executor(
                None, client.application_report, app_id
            )
            state = str(report.state)
            if state in {'FAILED', 'KILLED', 'FINISHED'}:
                raise Exception("Application %s failed to start, check "
                                "application logs for more information"
                                % app_id)
            elif state == 'RUNNING':
                self.current_ip = report.host
                break
            else:
                await gen.sleep(0.5)

        # Wait for port to be set
        while self.current_port == 0:
            await gen.sleep(0.5)

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
        state = str(report.state)
        if state == 'FAILED':
            return 1
        elif state in {'KILLED', 'FINISHED'}:
            return 0
        else:
            return None

    async def stop(self, now=False):
        if self.app_id == '':
            return

        client = await self._get_client()
        await gen.IOLoop.current().run_in_executor(
            None, client.kill_application, self.app_id
        )
