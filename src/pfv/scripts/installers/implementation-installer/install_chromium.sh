cd $HOME/TVOQE_UPGRADE_27/quic/

#Install depot_tools
[ ! -f $HOME/TVOQE_UPGRADE_27/quic/depot_tools ] && git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="$PATH:$HOME/TVOQE_UPGRADE_27/quic/depot_tools"
echo export PATH="$PATH:$HOME/TVOQE_UPGRADE_27/quic/depot_tools" >> ~/.profile 

#Install chromium
mkdir chromium
cd chromium
[ ! -f $HOME/TVOQE_UPGRADE_27/quic/chromium/src ] && fetch --nohooks chromium
cd src
[ ! -f $HOME/TVOQE_UPGRADE_27/quic/chromium/src ] && ./build/install-build-deps.sh
[ ! -f $HOME/TVOQE_UPGRADE_27/quic/chromium/src ] && gclient runhooks
[ ! -f $HOME/TVOQE_UPGRADE_27/quic/chromium/src/out/Default ] && gn gen out/Default
#autoninja -C out/Default chrome
ninja -C out/Default quic_server
ninja -C out/Default quic_client


