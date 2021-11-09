FROM ubuntu:20.04

RUN apt-get update && apt-get install -y wget tar git

RUN wget https://dl.google.com/go/go1.14.linux-amd64.tar.gz && \
  tar xfz go1.14.linux-amd64.tar.gz && \
  rm go1.14.linux-amd64.tar.gz

ENV PATH="/go/bin:${PATH}"

# build with --build-arg CACHEBUST=$(date +%s)
ARG CACHEBUST=1

RUN git clone https://github.com/lucas-clemente/quic-go && \
  cd quic-go && git checkout v0.18.1 && \
  go get ./...

RUN mkdir /client /server
RUN mkdir /logs

COPY main.go /client/
COPY server/main.go /server/

WORKDIR /quic-go

RUN go build -o /client/client /client/main.go
RUN go build -o /server/server /server/main.go

COPY run_endpoint.sh /
RUN chmod +x /run_endpoint.sh

WORKDIR /logs

ENTRYPOINT [ "/run_endpoint.sh" ]