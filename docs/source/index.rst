yarnspawner
===========

A custom Spawner_ for JupyterHub_ that launches notebook servers on Apache
Hadoop/YARN clusters.

.. contents:: :local:


Installation
------------

YarnSpawner should be installed in the same environment and node as JupyterHub
(usually an edge node). It can be installed using Conda_, Pip, or from source.

**Install with Conda:**

.. code::

    conda install -c conda-forge jupyterhub-yarnspawner

**Install with Pip:**

.. code::

    pip install jupyterhub-yarnspawner

**Install from source:**

.. code::

    git clone https://github.com/jcrist/yarnspawner.git
    cd yarnspawner
    pip install .


Configuration
-------------

``YarnSpawner`` requires some configuration and setup to use. This will vary
depending on your cluster, but will follow the same general procedure.

This assumes that you've already generated a ``jupyterhub_config.py`` file, as
described in the `JupyterHub configuration documentation`_.

For documentation on all available options see :doc:`options`.


Set the JupyterHub Spawner Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tell JupyterHub to use ``YarnSpawner`` by adding the following line to your
``jupyterhub_config.py``:

.. code-block:: python

    c.JupyterHub.spawner_class = 'yarnspawner.YarnSpawner'


Enable Proxy User Permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

YarnSpawner makes full use of Hadoop's security model, and will start Jupyter
notebook server's in containers with the requesting user's permissions (e.g. if
``alice`` logs in to JupyterHub, their notebook server will be running as user
``alice``). To accomplish this, JupyterHub needs `proxy user`_ permissions.
This allows the JupyterHub server to perform actions impersonating another user.

To enable this you'll need to do the following:

1. Create a user for JupyterHub to run under. Here we'll use ``jupyterhub``.

2. Enable `proxy user`_ permissions for this user. The users ``jupyterhub`` has
   permission to impersonate can be restricted to certain groups, and requests
   to impersonate may be restricted to certain hosts. At a minimum,
   ``jupyterhub`` will require permission to impersonate any JupyterHub user,
   with requests allowed from at least the host running JupyterHub.

   .. code-block:: xml

      <property>
        <name>hadoop.proxyuser.jupyterhub.hosts</name>
        <value>host-where-jupyterhub-is-running</value>
      </property>
      <property>
        <name>hadoop.proxyuser.jupyterhub.groups</name>
        <value>group1,group2</value>
      </property>

   If looser restrictions are acceptable, you may also use the wildcard ``*``
   to allow impersonation of any user or from any host.

   .. code-block:: xml

      <property>
        <name>hadoop.proxyuser.jupyterhub.hosts</name>
        <value>*</value>
      </property>
      <property>
        <name>hadoop.proxyuser.jupyterhub.groups</name>
        <value>*</value>
      </property>

   See the `proxy user`_ documentation for more information.


Enable Kerberos Security (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your cluster has Kerberos enabled, you'll also need to create a principal
and keytab for the JupyterHub user (we'll continue using ``jupyterhub`` for
this, as above).

.. code-block:: shell

    # Create the jupyterhub principal
    $ kadmin -q "addprinc -randkey jupyterhub@YOUR_REALM.COM"

    # Create a keytab
    $ kadmin -q "xst -norandkey -k /path/to/jupyterhub.keytab

Store the keytab file wherever you see fit (we recommend storing it along with
the jupyterhub configuration). You'll also want to make sure that
``jupyterhub.keytab`` is only readable by the ``jupyterhub`` user.

.. code-block:: shell

    $ sudo chown jupyterhub /path/to/jupyterhub.keytab
    $ sudo chmod 400 /path/to/jupyterhub.keytab

To configure JupyterHub to use this keytab file, you'll need to add the
following line to your ``jupyterhub_config.py``:

.. code-block:: python

    # The principal JupyterHub is running as
    c.YarnSpawner.principal = 'jupyterhub'

    # Path to the keytab you created
    c.YarnSpawner.keytab = '/path/to/jupyterhub.keytab'


Specifying Python Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the user's notebook servers will be each running in their own YARN
container, you'll need to provide a way for Python environments to be available
to these containers. You have a few options here:

- Install identical Python environments on every node
- Archive environments to be distributed to the container at runtime (recommended)

In either case, the Python environment requires at minimum:

- ``yarnspawner``
- ``jupyterhub``
- ``notebook``


Using a Local Environment
^^^^^^^^^^^^^^^^^^^^^^^^^

If you've installed identical Python environments on every node, you only need
to configure ``YarnSpawner`` to use the provided Python. This could be done a
few different ways:


.. code-block:: python

    # Use the path to python in the startup command
    c.YarnSpawner.cmd = '/path/to/python -m yarnspawner.singleuser'

    # OR
    # Activate a local conda environment before startup
    c.YarnSpawner.prologue = 'conda activate /path/to/your/environment'

    # OR
    # Activate a virtual environment before startup
    c.YarnSpawner.prologue = 'source /path/to/your/environment/bin/activate'


Using an Archived Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

YARN also provides mechanisms to "localize" files/archives to a container
before starting the application. This can be used to distribute Python
environments at runtime. This approach is appealing in that it doesn't require
installing anything throughout the cluster, and allows for centrally managing
your user's Python environments.

Packaging environments for distribution is usually accomplished using

- conda-pack_ for conda_ environments
- venv-pack_  for virtual environments (both venv_ and virtualenv_ supported)

Both are tools for taking an environment and creating an archive of it in a way
that (most) absolute paths in any libraries or scripts are altered to be
relocatable. This archive then can be distributed with your application, and
will be automatically extracted during `YARN resource localization`_

Below we demonstrate creating and Packaging a python environment containing all
the required jupyter packages, as well as ``pandas`` and ``scikit-learn``.
Additional packages could be added as needed.


**Packaging a Conda Environment with Conda-Pack**

.. code-block:: bash

    # Create a new conda environment
    $ conda create -c conda-forge -y -n example
    ...

    # Activate the environment
    $ conda activate example

    # Install the needed packages
    $ conda install -c conda-forge -y \
    conda-pack \
    jupyterhub-yarnspawner \
    pandas \
    scikit-learn
    ...

    # Pip required to avoid hardcoded path in kernelspec (for now)
    $ pip install notebook

    # Package the environment into environment.tar.gz
    $ conda pack -o environment.tar.gz
    Collecting packages...
    Packing environment at '/home/jcrist/miniconda/envs/example' to 'environment.tar.gz'
    [########################################] | 100% Completed | 24.2s


**Packaging a Virtual Environment with Venv-Pack**

.. code-block:: bash

    # Create a virtual environment
    $ python -m venv example            # Using venv
    $ python -m virtualenv example      # Or using virtualenv
    ...

    # Activate the environment
    $ source example/bin/activate

    # Install the needed packages
    $ pip install \
    venv-pack \
    jupyterhub-yarnspawner \
    notebook \
    pandas \
    scikit-learn
    ...

    # Package the environment into environment.tar.gz
    $ venv-pack -o environment.tar.gz
    Collecting packages...
    Packing environment at '/home/jcrist/environments/example' to 'environment.tar.gz'
    [########################################] | 100% Completed |  12.4s

Note that the python linked to in the virtual environment must exist and be
accessible on every node in the YARN cluster. If the environment was created
with a different Python, you can change the link path using the
``--python-prefix`` flag. For more information see the `venv-pack
documentation`_.

**Using the Packaged Environment**

It is recommended to upload the environments to some directory on HDFS
beforehand, to avoid repeating the upload cost for every user. This directory
should be readable by all users, but writable only by the admin user managing
Python environments (here we'll use the ``jupyterhub`` user).

.. code-block:: shell

    $ hdfs dfs -mkdir /path/to/environments
    $ hdfs dfs -chown jupyterhub /path/to/environments
    $ hdfs dfs -chmod 744 /path/to/environments

To use the packaged environment with ``YarnSpawner``, you need to include
the archive in ``YarnSpawner.localize_files``, and activate the environment in
``YarnSpawner.prologue``. This looks the same for environments packaged using
either tool.

.. code-block:: python

    c.YarnSpawner.localize_files = {
        'environment': {
            'source': 'hdfs:///path/to/environments/environment.tar.gz',
            'visibility': 'public'
        }
    }
    c.YarnSpawner.prologue = 'source environment/bin/activate'


Note that we set ``visibility`` to ``public`` for the environment, so that
multiple users can all share the same localized environment (reducing the cost
of moving the environments around).

For more information, see the `Skein documentation on distributing files`_.


Additional Configuration Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``YarnSpawner`` has several additional configuration fields. See :doc:`options`
for documentation on all available options. At a minimum you'll probably want
to configure the memory and cpu limits, as well as which YARN queue to use.

.. code-block:: python

    # The memory limit for a notebook instance.
    c.YarnSpawner.mem_limit = '2 G'

    # The cpu limit for a notebook instance
    c.YarnSpawner.cpu_limit = 1

    # The YARN queue to use
    c.YarnSpawner.queue = '...'


Example
~~~~~~~

In summary, an example ``jupyterhub_config.py`` configuration enabling
``yarnspawner`` might look like:

.. code-block:: python

    # Enable yarnspawner
    c.JupyterHub.spawner_class = 'yarnspawner.YarnSpawner'

    # Configuration for kerberos security
    c.YarnSpawner.principal = 'jupyterhub'
    c.YarnSpawner.keytab = '/etc/jupyer/jupyter.keytab'

    # Resource limits per-user
    c.YarnSpawner.mem_limit = '2 G'
    c.YarnSpawner.cpu_limit = 1

    # The YARN queue to use
    c.YarnSpawner.queue = 'jupyterhub'

    # Specify location of the archived Python environment
    c.YarnSpawner.localize_files = {
        'environment': {
            'source': 'hdfs:///path/to/environments/environment.tar.gz',
            'visibility': 'public'
        }
    }
    c.YarnSpawner.prologue = 'source environment/bin/activate'


Additional Resources
--------------------

If you're interested in ``yarnspawner``, you may also be interested in a few
other libraries:

- jupyter-hdfscm_: A Jupyter ContentsManager_ for storing notebooks on HDFS.
  This can be used with ``yarnspawner`` to provide a way to persist notebooks
  between sessions.
- pyarrow_: Among other things, this Python library provides efficient access
  to HDFS, as well as the Parquet, and ORC file formats.
- dask-yarn_: A library for deploying Dask_ on YARN. This
  library works fine with ``yarnspawner``, allowing users to launch Dask
  clusters from inside notebooks started by ``yarnspawner``.
- findspark_: A library enabling using PySpark_ as a normal Python library.
  This can be used to enable users to launch Spark clusters from inside
  notebooks started by ``yarnspawner``.
- skein_: Both ``yarnspawner`` and ``dask-yarn`` are built on ``skein``, a
  library for writing and deploying generic applications on YARN.


.. toctree::
    :maxdepth: 2
    :hidden:

    options.rst


.. _spawner: https://github.com/jupyterhub/jupyterhub/wiki/Spawners
.. _jupyterhub: https://jupyterhub.readthedocs.io/
.. _proxy user: https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-common/Superusers.html
.. _JupyterHub configuration documentation: https://jupyterhub.readthedocs.io/en/stable/getting-started/config-basics.html
.. _conda-pack: https://conda.github.io/conda-pack/
.. _conda: http://conda.io/
.. _venv:
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _venv-pack documentation:
.. _venv-pack: https://jcrist.github.io/venv-pack/
.. _YARN resource localization: https://hortonworks.com/blog/resource-localization-in-yarn-deep-dive/
.. _Skein documentation on distributing files: https://jcrist.github.io/skein/distributing-files.html
.. _jupyter-hdfscm: https://jcrist.github.io/hdfscm/
.. _pyarrow: https://arrow.apache.org/docs/python/
.. _skein: https://jcrist.github.io/skein/
.. _ContentsManager: https://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html
.. _dask-yarn: https://yarn.dask.org/
.. _Dask: https://dask.org/
.. _findspark: https://github.com/minrk/findspark
.. _PySpark: https://spark.apache.org/docs/0.9.0/python-programming-guide.html
