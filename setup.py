from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

requirements = [
    'jupyterhub',
    'skein',
]

setup(name='yarnspawner',
      version='0.0.1',
      license='BSD',
      maintainer='Jim Crist',
      maintainer_email='jiminy.crist@gmail.com',
      description='JupyterHub Spawner for Apache Hadoop/YARN Clusters',
      long_description=long_description,
      packages=['yarnspawner'],
      install_requires=requirements)
