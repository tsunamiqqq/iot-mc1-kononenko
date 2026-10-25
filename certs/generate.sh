cd certs
openssl req -new -x509 -days 365 -nodes -keyout ca.key -out ca.crt -sha256 -subj "/C=UA/O=IoT-MC1/CN=My-Root-CA"
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/C=UA/O=IoT-MC1/CN=mqtt_broker"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -sha256
cd ..