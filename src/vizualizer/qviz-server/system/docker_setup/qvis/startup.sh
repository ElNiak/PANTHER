#!/bin/sh
# it is VERY IMPORTANT this file is saved with LF line-ending (not CRLF) or it won't work!

echo "Pulling from qvis-server repo to update system/docker_setup/startup/startup.sh"
cd /srv/qvisserver
git checkout -- package-lock.json # for some very strange and unknown reason, this gets updated locally before the pull... drop those changes
git reset --hard HEAD # prevent issues like those with packet-lock.json above more generally
git pull origin master


echo "Executing the actual startup.sh"
# chmod sometimes takes too long, causing the .sh script to not be executed ("Text file is busy" bug)
# sync helps by waiting for chmod to fully complete
chmod 777 /srv/qvisserver/system/docker_setup/startup/startup.sh
sync
/srv/qvisserver/system/docker_setup/startup/startup.sh "$@"
