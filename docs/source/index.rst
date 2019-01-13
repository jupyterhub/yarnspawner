yarnspawner
===========

A custom Spawner_ for JupyterHub_ that launches notebook servers on Apache
Hadoop/YARN clusters.


Installation
------------

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


.. toctree::
    :maxdepth: 2

    options.rst


.. _spawner: https://github.com/jupyterhub/jupyterhub/wiki/Spawners
.. _jupyterhub: https://jupyterhub.readthedocs.io/
