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
        'omegaconf',
        'cerberus',
        'jinja2',
        'requests',
        'PyYAML',
        "docker",
        "hypothesis",
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

