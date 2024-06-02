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

# TODO test if good

setup(name='panther-webapp',
      version='0.1',
      description='panther-webapp',
      long_description=long_description,
      #url='https://github.com/csvl/SEMA-ToolChain/tree/production',
      author='ElNiak from UCLouvain',
      author_email='nomail@uclouvain.com',
      license='MIT', 
      packages=find_packages(), 
      setup_requires=['wheel'], # "importlib-metadata", ,"importlib_metadata"
      install_requires=[
          'flask', # malwexp
          "flask_session",
          "django",
          "flask-socketio",
          "requests",
          "Flask-Cors==3.0.10",
          "npf-web-extension",
          'execnet', 
          'pytest',
          "pexpect",
          "chardet",
          "gperf",
          "pandas",
          "scandir",
          "ply",
          # "PyQt5",
          "plantuml",
          "pygraphviz",
          "scapy",
          "importlib_metadata",
          'termcolor',
          'terminal_banner'
          # "pytracemalloc",
          #"pytracemalloc==0.9.1"
          ],
      zip_safe=False)
