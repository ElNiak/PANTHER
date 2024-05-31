cd $HOME/TVOQE_UPGRADE_27/quic
git clone https://github.com/h2o/quicly.git
cd $HOME/TVOQE_UPGRADE_27/quic/quicly
git checkout kazuho/draft-29
git submodule update --init --recursive
cmake .
make

curl -sL https://cpanmin.us | perl - --sudo --self-upgrade
cpanm --installdeps --notest --sudo .

make check

