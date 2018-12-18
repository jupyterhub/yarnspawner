import versioneer
from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

setup(name='jupyterhub-yarnspawner',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      license='BSD',
      maintainer='Jim Crist',
      maintainer_email='jiminy.crist@gmail.com',
      description='JupyterHub Spawner for Apache Hadoop/YARN Clusters',
      long_description=long_description,
      url='http://github.com/jcrist/yarnspawner',
      project_urls={
          'Source': 'https://github.com/jcrist/yarnspawner',
          'Tracker': 'https://github.com/jcrist/yarnspawner/issues',
      },
      packages=['yarnspawner'],
      python_requires='>=3.5',
      install_requires=[
          'jupyterhub>=0.8',
          'skein',
      ],
      entry_points='''
          [console_scripts]
          yarnspawner-singleuser=yarnspawner.singleuser:main
      ''')
