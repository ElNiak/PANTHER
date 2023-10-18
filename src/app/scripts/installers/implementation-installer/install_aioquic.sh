cd $PROOTPATH/quic-implementations/aioquic
curl https://sh.rustup.rs -sSf | sh -s -- -y
git stash
git fetch
git checkout d272be10b93b09b75325b139090007dae16b9f16
git pull
export PYTHONPATH=${PYTHONPATH}:$PWD
source $HOME/.cargo/env

sudo apt install --yes software-properties-common
sudo add-apt-repository --yes ppa:deadsnakes/ppa
sudo apt install --yes python3.9
sudo apt install --yes python3.9-distutils
sudo apt install --yes python3.9-dev

python3.9 -m pip uninstall --yes setuptools
python3.9 -m pip uninstall --yes cryptography
python3.9 -m pip uninstall --yes cffi
python3.9 -m pip uninstall --yes setuptools-rust
python3.9 -m pip uninstall -e .

python3.9 -m pip install werkzeug==2.0.3
python3.9 -m pip install --upgrade pip
python3.9 -m pip install --upgrade distlib
python3.9 -m pip install --upgrade launchpadlib
python3.9 -m pip install --upgrade setuptools
python3.9 -m pip install --upgrade cryptography
python3.9 -m pip install --upgrade cffi
python3.9 -m pip install setuptools-rust
python3.9 -m pip install -e .
python3.9 -m pip install aiofiles asgiref dnslib httpbin starlette wsproto

rm $PROOTPATH/quic-implementations/aioquic/examples/http3_client.py # TODO check
cp $PROOTPATH/ressources/aioquic/rfc9000/http3_client.py $PROOTPATH/quic-implementations/aioquic/examples/http3_client.py
