# PANTHER-SCP/panther/setup.py

from setuptools import setup, find_packages

setup(
    name='Panther',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'omegaconf',
        'cerberus',
        'jinja2',
        'requests',
        'PyYAML',
        "docker"
    ],
    entry_points={
        'console_scripts': [
            'panther-cli=panther_cli:main',
        ],
    },
    author='ElNiak',
    author_email='your.email@example.com',
    description='Panther: Secure Communication Platform',
    url='https://github.com/ElNiak/PANTHER',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
