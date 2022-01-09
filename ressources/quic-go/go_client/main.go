package main

import (
	"bytes"
	"crypto/tls"
	"crypto/x509"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/lucas-clemente/quic-go"
	"github.com/lucas-clemente/quic-go/interop/http09"
	//"github.com/lucas-clemente/quic-go/interop/utils"
	"github.com/lucas-clemente/quic-go/internal/protocol"
)

type logger struct {
	enabled bool
}

func (l *logger) Logf(format string, v ...interface{}) {
	if l.enabled {
		log.Printf(format, v...)
	}
}

func main() {
	verbose := flag.Bool("v", false, "verbose")
	printData := flag.Bool("P", false, "printData the data")
	doVN := flag.Bool("V", false, "version negociation")
	keyLogFile := flag.String("X", "", "key log file")
	requestSize := flag.Int("G", 50000, "amount of bytes to ask for in the request")
	flag.Bool("R", false, "force RTT connection establishment")

	//secure := flag.Bool("secure", false, "do certificate verification")
	flag.Parse()
	address := flag.Arg(0)
	port := flag.Arg(1)

	logger := &logger{}

	if !*verbose {
		logger.enabled = false
	}

	var keyLog io.Writer
	if len(*keyLogFile) > 0 {
		f, err := os.Create(*keyLogFile)
		if err != nil {
			log.Fatal(err)
		}
		defer f.Close()
		keyLog = f
	}

	pool, err := x509.SystemCertPool()
	if err != nil {
		log.Fatal(err)
	}

	// a quic.Config that doesn't do a Retry
	quicConf := &quic.Config{
		AcceptToken: func(_ net.Addr, _ *quic.Token) bool { return true },
		ConnectionIDLength: 8,
		//Tracer:      qlog.NewTracer(getLogWriter),
		//DisablePathMTUDiscovery: true,
	}
	if *doVN {
		quicConf = &quic.Config{
			AcceptToken: func(_ net.Addr, _ *quic.Token) bool { return true },
			ConnectionIDLength: 8,
			Versions: [] protocol.VersionNumber{0x22334455, 0xff00001d, 0x33445566},
			//Tracer:      qlog.NewTracer(getLogWriter),
			//DisablePathMTUDiscovery: true,
		}
	} 
	
	roundTripper := &http09.RoundTripper{
		TLSClientConfig: &tls.Config{
			RootCAs:            pool,
			InsecureSkipVerify: true,
			KeyLogWriter:       keyLog,
		},
		QuicConfig: quicConf,
	}
	defer roundTripper.Close()
	hclient := &http.Client{
		Transport: roundTripper,
	}

	var wg sync.WaitGroup
	urls := []string{fmt.Sprintf("https://%s:%s/%d", address, port, *requestSize)}
	wg.Add(len(urls))
	for _, addr := range urls {
		logger.Logf("GET %s", addr)
		go func(addr string) {
			now := time.Now()
			rsp, err := hclient.Get(addr)
			if err != nil {
				log.Fatal(err)
			}
			logger.Logf("Got response for %s: %#v", addr, rsp)

			if *printData {
				body := &bytes.Buffer{}
				_, err = io.Copy(body, rsp.Body)
				if err != nil {
					log.Fatal(err)
				}
				logger.Logf("Request Body:")
				logger.Logf("%s", body.Bytes())
			} else {
				// discard everything but read the buffer
				n, err := io.Copy(ioutil.Discard, rsp.Body)
				if err != nil {
					log.Fatal(err)
				}
				elapsed := time.Now().Sub(now)
				fmt.Printf("%f ms\n", float64(elapsed.Microseconds())/1000.0)
				println("done")
				logger.Logf("Got %d bytes", n)
			}
			wg.Done()
		}(addr)
	}
	wg.Wait()
}