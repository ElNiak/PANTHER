FROM ubuntu:18.04  

# Install dependencies

RUN apt-get update  && apt-get -y install alien
RUN apt-get install -y apt-utils git

RUN git clone --recurse-submodules https://github.com/ElNiak/QUIC-FormalVerification.git

WORKDIR /QUIC-FormalVerification/scripts/installers
RUN apt-get install  --fix-missing  -y git python3 python3-dev python3-pip build-essential 
RUN python3 update-for-docker.py
RUN bash install.sh
WORKDIR /QUIC-FormalVerification
ARG MODE
ARG CATE
ARG TIME
ARG IMPL
ARG ITER
RUN python3 run_experiments.py --not_docker --mode $MODE --categories $CATE --update_include_tls  --timeout $TIME --getstats  --implementations $IMPL --iter $ITER --compile

