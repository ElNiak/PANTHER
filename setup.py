from setuptools import setup, find_packages
import codecs
import os
import platform

# Get the long description from the README file
here = os.path.abspath(os.path.dirname(__file__))
try:
  with codecs.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
      long_description = f.read()
except:
  # This happens when running tests
  long_description = None

setup(
    name='Panther',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        # For panther
        'omegaconf',
        'cerberus',
        'jinja2',
        'requests',
        'PyYAML',
        "docker",
        "hypothesis",
        "pytest",
        # For panther-web
        'flask', # malwexp
        "flask_session",
        "flask_wtf",
        "django",
        "flask-socketio",
        "requests",
        "Flask-Cors==4.0.1",
        "npf-web-extension",
        'execnet', 
        'pytest',
        "pexpect",
        "chardet",
        "gperf",
        "pandas",
        "scandir",
        "ply",
        "plantuml",
        "pygraphviz",
        "scapy",
        "importlib_metadata",
        'termcolor',
        'terminal_banner'
    ],
    entry_points={
        'console_scripts': [
            'panther=panther_cli:main',
        ],
    },
    author='ElNiak',
    author_email='your.email@example.com',
    description='Panther: Secure Communication Platform',
    long_description=long_description,
    url='https://github.com/ElNiak/PANTHER',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)

