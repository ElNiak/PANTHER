# /app/setup.py
from setuptools import setup, find_packages

setup(
    name='PFV',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'pexpect',
        'chardet',
        'gperf',
        'pandas',
        'scandir',
        'ply',
        'PyQt5',
        'plantuml',
        'pygraphviz',
        'requests',
        'scapy',
        #'importlib_metadata'
        # "progressbar2"
    ],
    entry_points={
        'console_scripts': [
            # Add any command line scripts here
        ],
    },
)
