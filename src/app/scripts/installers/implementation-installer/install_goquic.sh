#Clone quic-go project
cd /
#Install go
sudo wget https://dl.google.com/go/go1.16.linux-amd64.tar.gz  &> /dev/null
sudo rm -r /go
sudo tar xfz go1.16.linux-amd64.tar.gz &> /dev/null
sudo rm go1.16.linux-amd64.tar.gz
export PATH="/go/bin:${PATH}"

#Install project
cd $PROOTPATH/quic-implementations/quic-go/
git stash
git fetch
git checkout b5ef99a32c250fc63f89cc686c13a008c5419d01 #v0.18.1 # v0.20.0
mkdir client server
echo "go get"
cp $PROOTPATH/ressources/quic-go/rfc9000/go_client/main.go $PROOTPATH/quic-implementations/quic-go/client/main.go
cp $PROOTPATH/ressources/quic-go/rfc9000/go_server/main.go $PROOTPATH/quic-implementations/quic-go/server/main.go
cp $PROOTPATH/ressources/quic-go/rfc9000/connection_id.go $PROOTPATH/quic-implementations/quic-go/internal/protocol/connection_id.go

go mod init github.com/lucas-clemente/quic-go
go get ./...
go build -o $PROOTPATH/quic-implementations/quic-go/client/client $PROOTPATH/quic-implementations/quic-go/client/main.go
go build -o $PROOTPATH/quic-implementations/quic-go/server/server $PROOTPATH/quic-implementations/quic-go/server/main.go

