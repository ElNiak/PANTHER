# server
docker run -ti -e ROLE=server --network host --mount type=bind,source="$(pwd)"/cert,target=/certs ngtcp2-generic -p 4445 -k /certs/server.key -c /certs/server.crt

# client
docker run -ti -e ROLE=client --network host --mount type=bind,source="$(pwd)",target=/logs ngtcp2-generic -G 50000000 -X keys.log 127.0.0.1 4445
