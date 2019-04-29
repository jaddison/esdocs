from codecs import open
from setuptools import setup, find_packages
from os import path

import esdocs

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='esdocs',
    version=esdocs.__version__,
    description='Serialization & bulk indexing package for Elasticsearch; based on elasticsearch-dsl.py, supports multi-processing, Django',
    long_description=long_description,
    keywords='elasticsearch django multiprocessing gevent gipc asynchronous bulk index serialization',

    license='MIT',
    author='jaddison',
    author_email='addi00+github.com@gmail.com',
    url='https://github.com/jaddison/esdocs',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Database',
        'Topic :: System :: Networking',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
    ],

    packages=find_packages(),
    py_modules=['esdocs'],

    python_requires='>=3.4',
    install_requires=[
        'elasticsearch-dsl>6.2.1,<7'
    ],
    extras_require={
        'gevent': ['gevent', 'gipc']
    },

    entry_points = {
        'console_scripts': [
            'esdocs=esdocs.utils:run',
            'esdocs-django=esdocs.contrib.esdjango.run:run',
        ],
    }
)
