cd $PROOTPATH/quic-implementations/aioquic
export PYTHONPATH=$PWD
python3 -m pip install setuptools_rust
python3 -m pip install -e .
python3 -m pip install aiofiles asgiref dnslib httpbin starlette wsproto
