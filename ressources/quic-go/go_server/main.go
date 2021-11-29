package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"log"
	"math"
	"math/rand"
	"net"
	"net/http"
	"os"
	//"strconv"

	"github.com/lucas-clemente/quic-go"
	"github.com/lucas-clemente/quic-go/http3"
	"github.com/lucas-clemente/quic-go/interop/http09"
	"github.com/lucas-clemente/quic-go/interop/utils"
)

var tlsConf *tls.Config

func main() {
	certFile := flag.String("c", "/certs/cert.pem", "cert file")
	keyFile := flag.String("k", "/certs/priv.key", "private key file")
	port := flag.Int("p", 443, "port to bind on")
	flag.Parse()

	log.SetOutput(os.Stdout)

	keyLog, err := utils.GetSSLKeyLog()
	if err != nil {
		fmt.Printf("Could not create key log: %s\n", err.Error())
		os.Exit(1)
	}
	if keyLog != nil {
		defer keyLog.Close()
	}
	log.Printf("test")


	// a quic.Config that doesn't do a Retry
	quicConf := &quic.Config{
		AcceptToken: func(_ net.Addr, _ *quic.Token) bool { return true },
		ConnectionIDLength: 8,    
        HandshakeIdleTimeout: 0,
        MaxIdleTimeout: 0,
		//Tracer: qlog.NewTracer(getLogWriter),
	}

	cert, err := tls.LoadX509KeyPair(*certFile, *keyFile)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	tlsConf = &tls.Config{
		Certificates: []tls.Certificate{cert},
		KeyLogWriter: keyLog,
	}
	err = runHTTP09Server(quicConf, *port)

	if err != nil {
		fmt.Printf("Error running server: %s\n", err.Error())
		os.Exit(1)
	}
}

func runHTTP09Server(quicConf *quic.Config, port int) error {
	server := http09.Server{
		Server: &http.Server{
			Addr:      fmt.Sprintf(":%d", port),
			TLSConfig: tlsConf,
		},
		QuicConfig: quicConf,
	}

	handler := &bufferHandler{make([]byte, 5000000)}
	http.DefaultServeMux.Handle("/index.html", handler)
	log.Printf("start server")
	return server.ListenAndServe()
}

type bufferHandler struct {
	buffer []byte
}

var _ http.Handler = &bufferHandler{}

func (h *bufferHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		w.WriteHeader(404)
		return
	}
	if r.URL.Path[0] != '/' {
		w.WriteHeader(404)
		return
	}
	/*size, err := strconv.Atoi(r.URL.Path[1:])
	if err != nil {
		log.Fatalf("wrong URL path: %s: %+v", r.URL.Path, err)
		return
	}*/
	size := 50000;
	w.WriteHeader(200)
	var written int = 0
	for written < size {
		n, err := rand.Read(h.buffer)
		if err != nil {
			log.Fatalf("error getting random bytes: %+v", err)
		}
		n, err = w.Write(h.buffer[:int(math.Min(float64(len(h.buffer)), float64(size - written)))])
		if err != nil {
			log.Fatalf("error writing the header: %+v", err)
		}
		written += n
	}
}


func runHTTP3Server(quicConf *quic.Config, port int) error {
	server := http3.Server{
		Server: &http.Server{
			Addr:      fmt.Sprintf(":%d", port),
			TLSConfig: tlsConf,
		},
		QuicConfig: quicConf,
	}
	handler := &bufferHandler{make([]byte, 5000000)}
	http.DefaultServeMux.Handle("/", handler)
	return server.ListenAndServe()
}