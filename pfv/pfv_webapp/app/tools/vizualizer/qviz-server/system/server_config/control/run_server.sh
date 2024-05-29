#!/bin/sh

# typical way to call this: ./run_server.sh

# make sure we always have the latest certs from let's encrypt loaded
cp /etc/letsencrypt/live/quictools.info/privkey.pem /home/qvis-server/trunk/system/docker_setup/qvis/tls_cert.key
cp /etc/letsencrypt/live/quictools.info/fullchain.pem /home/qvis-server/trunk/system/docker_setup/qvis/tls_cert.crt

sudo docker stop qvisserver && sudo docker rm qvisserver  
# we override the /srv/certs with a locally mounted dir so we don't have to rebuild the image when the certs change.
sudo docker run --privileged --name qvisserver -p 8443:443 --restart unless-stopped --volume=/home/qvis-server/trunk/system/docker_setup/qvis:/srv/certs --volume=/srv/qvis-cache:/srv/qvis-cache -d qvis/server:latest "$@"

# -p 8089:80
