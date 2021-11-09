#Clone quic-go project
cd $PROOTPATH/quic-implementations/
#Install go
wget https://dl.google.com/go/go1.14.linux-amd64.tar.gz  &> /dev/null
tar xfz go1.14.linux-amd64.tar.gz &> /dev/null
rm go1.14.linux-amd64.tar.gz
#Install project
cd quic-go/
export PATH="/go/bin:${PATH}"
mkdir client server
go get ./...
go build -o $PROOTPATH/quic-implementations/quic-go/client/client $PROOTPATH/ressources/go_client/main.go
go build -o $PROOTPATH/quic-implementations/quic-go/server/server $PROOTPATH/ressources/go_server/main.go

