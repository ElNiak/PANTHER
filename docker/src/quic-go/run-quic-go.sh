# client

docker run -ti -e ROLE=client --network host --mount type=bind,source=${HOME}/go/src/github.com/lucas-clemente/quic-go/internal/testdata,target=/certs --mount type=bind,source="$(pwd)",target=/logs quic-go-generic -G 50000 -X keys.log 127.0.0.1 4445



# server

docker run -ti -e ROLE=server --network host --mount type=bind,source=${HOME}/go/src/github.com/lucas-clemente/quic-go/internal/testdata,target=/certs quic-go-generic -p 4445
