FROM ubuntu:18.04

# Install dependencies

RUN apt-get update  && apt-get -y install alien
RUN apt-get install -y apt-utils git

RUN git clone --recurse-submodules https://github.com/ElNiak/QUIC-FormalVerification.git

WORKDIR /QUIC-FormalVerification/scripts/installers
RUN bash install.sh
RUN /usr/bin/python3 /home/user/Documents/QUIC-RFC9000/run_experiments.py --mode client --categories retry_test --update_include_tls  --timeout 30 --getstats  --implementations quant picoquic --iter 2 --compile

