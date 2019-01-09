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
          'Issue Tracker': 'https://github.com/jcrist/yarnspawner/issues',
          'Documentation': 'https://jcrist.github.io/yarnspawner/'
      },
      keywords='YARN HDFS hadoop jupyterhub',
      classifiers=['Topic :: System :: Systems Administration',
                   'Topic :: System :: Distributed Computing',
                   'License :: OSI Approved :: BSD License',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3'],
      packages=['yarnspawner'],
      python_requires='>=3.5',
      install_requires=['jupyterhub>=0.8', 'skein>=0.5.0'])
