# generate_certificates.sh

#!/bin/bash

# Create directories if they don't exist
mkdir -p config/certs
mkdir -p config/tls_keys

# Remove existing certificates and keys
rm -f config/certs/*.pem config/certs/*.csr
rm -f config/tls_keys/*.key

# Generate private key
openssl genrsa -out config/certs/key.pem 2048

# Generate certificate signing request (CSR)
openssl req -new -key config/certs/key.pem -out config/certs/cert.csr \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=localhost"

# Generate self-signed certificate
openssl x509 -req -days 365 -in config/certs/cert.csr -signkey config/certs/key.pem -out config/certs/cert.pem

# Generate ticket key (if applicable)
openssl rand -out config/tls_keys/ticket.key 48

echo "Certificates and keys generated successfully."
