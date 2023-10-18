import app from "./app";
import fs from "fs";
import https from "https";
import http from "http";

const port = 80; // 8088; // 80
const sport = 443; // 8089; // 443

https.createServer({
    key:  fs.readFileSync('/srv/certs/tls_cert.key'),
    cert: fs.readFileSync('/srv/certs/tls_cert.crt')
}, app)
    .listen(sport, function () {
        console.log('QVIS Server listening on port ' + sport);
    });

http.createServer(app).listen(port, function(){ console.log("QVIS Server listening on port " + port) }); 
