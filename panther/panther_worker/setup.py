# /app/setup.py
from setuptools import setup, find_packages

setup(
    name='PANTHER',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'flask', # malwexp
        "flask_session",
        "django",
        "requests",
        "Flask-Cors==4.0.1",
        "npf-web-extension",
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
        'termcolor',
        'terminal_banner'
        #'importlib_metadata'
        # "progressbar2"
    ],
    entry_points={
        'console_scripts': [
            # Add any command line scripts here
        ],
    },
)
