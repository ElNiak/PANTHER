#Clone quic-go project
cd /
#Install go
sudo wget https://dl.google.com/go/go1.14.linux-amd64.tar.gz  &> /dev/null
sudo tar xfz go1.14.linux-amd64.tar.gz &> /dev/null
sudo rm go1.14.linux-amd64.tar.gz
export PATH="/go/bin:${PATH}"

#Install project
cd $PROOTPATH/quic-implementations/quic-go/
git checkout v0.20.0
mkdir client server
go get ./...
go build -o $PROOTPATH/quic-implementations/quic-go/client/client $PROOTPATH/ressources/go_client/main.go
go build -o $PROOTPATH/quic-implementations/quic-go/server/server $PROOTPATH/ressources/go_server/main.go

