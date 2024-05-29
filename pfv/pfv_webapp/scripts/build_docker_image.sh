# Refresh dockers images for the swarm
export BASEPATH=$PWD

#Ivy container
cd $BASEPATH/src/services/streaming/
docker build -t artk-streaming 
