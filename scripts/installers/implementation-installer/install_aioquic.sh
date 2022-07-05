cd $PROOTPATH/quic-implementations/aioquic
curl https://sh.rustup.rs -sSf | sh -s -- -y
git stash
git checkout 0.9.3 
export PYTHONPATH=$PWD:/usr/bin/:$PYTHONPATH
#export PYTHONPATH=$PWD/src/aioquic:$PYTHONPATH
source $HOME/.cargo/env

python3.8 -m ensurepip --upgrade
python3.8 -m pip uninstall --yes setuptools
python3.8 -m pip uninstall --yes cryptography
python3.8 -m pip uninstall --yes cffi
python3.8 -m pip uninstall --yes setuptools-rust
python3.8 -m pip uninstall --yes werkzeug

python3.8 -m pip uninstall --yes setuptools --isolated
python3.8 -m pip uninstall --yes cryptography --isolated
python3.8 -m pip uninstall --yes cffi --isolated
python3.8 -m pip uninstall --yes setuptools-rust --isolated
python3.8 -m pip uninstall --yes werkzeug --isolated

python3.8 -m pip install --upgrade setuptools
python3.8 -m pip install --upgrade pip
python3.8 -m pip install --upgrade distlib
python3.8 -m pip install --upgrade setuptools-rust
python3.8 -m pip install --upgrade launchpadlib
python3.8 -m pip install --upgrade cryptography
python3.8 -m pip install --upgrade cffi
python3.8 -m pip install --upgrade werkzeug==2.0.3
python3.8 -m pip install .
python3.8 -m pip install -e .
python3.8 -m pip install aiofiles asgiref dnslib httpbin starlette wsproto

rm $PROOTPATH/quic-implementations/aioquic/examples/http3_client.py
cp $PROOTPATH/ressources/aioquic/http3_client.py $PROOTPATH/quic-implementations/aioquic/examples/http3_client.py
