FROM ubuntu:18.04  

# Install dependencies

RUN apt-get update  && apt-get -y install alien
RUN apt-get install -y apt-utils git

RUN git clone --recurse-submodules --branch quic-draft29 https://github.com/ElNiak/QUIC-FormalVerification.git

WORKDIR /QUIC-FormalVerification/scripts/installers
RUN apt-get install  --fix-missing  -y git python3 python3-dev python3-pip build-essential 
RUN python3 update-for-docker.py
RUN DEBIAN_FRONTEND="noninteractive" bash install.sh
RUN pip3 install progressbar
WORKDIR /QUIC-FormalVerification/utils
RUN python3 update-for-docker.py
WORKDIR /QUIC-FormalVerification
RUN python3 update-for-docker.py
ARG MODE
ARG CATE
ARG TIME
ARG IMPL
ARG ITER
# --implementations $IMPL
RUN python3 run_experiments.py --docker --mode $MODE --categories $CATE --update_include_tls  --timeout $TIME --getstats  --iter $ITER --compile

