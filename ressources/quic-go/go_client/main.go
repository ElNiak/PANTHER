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

type sessionCache struct {
	tls.ClientSessionCache
	put chan<- struct{}
}

func (l *logger) Logf(format string, v ...interface{}) {
	if l.enabled {
		log.Printf(format, v...)
	}
}

func newSessionCache(c tls.ClientSessionCache) (tls.ClientSessionCache, <-chan struct{}) {
	put := make(chan struct{}, 100)
	return &sessionCache{ClientSessionCache: c, put: put}, put
}

func (c *sessionCache) Put(key string, cs *tls.ClientSessionState) {
	c.ClientSessionCache.Put(key, cs)
	c.put <- struct{}{}
}


func main() {
	verbose := flag.Bool("v", false, "verbose")
	printData := flag.Bool("P", false, "printData the data")
	doVN := flag.Bool("V", false, "version negociation")
	keyLogFile := flag.String("X", "", "key log file")
	//requestSize := flag.Int("G", 50000, "amount of bytes to ask for in the request")
	use0RTT := flag.Bool("R", false, "force RTT connection establishment")

	//secure := flag.Bool("secure", false, "do certificate verification")
	flag.Parse()
	address := flag.Arg(0)
	port := flag.Arg(1)

	logger := &logger{}

	log.Printf("Got response for %t", use0RTT)

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

	tlsConf :=  &tls.Config{
		RootCAs:            pool,
		InsecureSkipVerify: true,
		KeyLogWriter:       keyLog,
	}

	var put <-chan struct{}
	tlsConf.ClientSessionCache, put = newSessionCache(tls.NewLRUClientSessionCache(1))

	roundTripper := &http09.RoundTripper{
		TLSClientConfig: tlsConf ,
		QuicConfig: quicConf,
	}

	defer roundTripper.Close()
	
	// hclient := &http.Client{
	// 	Transport: roundTripper,
	// }

	var url = fmt.Sprintf("https://%s:%s/%s", address, port, "index.html")
	var wg sync.WaitGroup
	urls := []string{url,url,url,url,url}
	wg.Add(len(urls))
	for _, addr := range urls {
		logger.Logf("GET %s", addr)
		go func(addr string) {
			now := time.Now()
			//rsp, err := hclient.Get(addr)
			method := http.MethodGet
			req, err := http.NewRequest(method, url, nil)
			if err != nil {
				log.Fatal(err)
			}
			rsp, err := roundTripper.RoundTrip(req)
			if err != nil {
				log.Fatal(err)
			}
			defer rsp.Body.Close()

			log.Printf("Got response for %s: %#v", addr, rsp)

			if *printData {
				body := &bytes.Buffer{}
				_, err = io.Copy(body, rsp.Body)
				if err != nil {
					log.Fatal(err)
				}
				log.Printf("Request Body:")
				log.Printf("%s", body.Bytes())
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
			//if !*use0RTT {
			log.Printf("wg.Done()")
			wg.Done()
			//}
		}(addr)
	}

	wg.Wait()
	
	// wait for the session ticket to arrive
	select {
	case <-time.NewTimer(10 * time.Second).C:
		log.Printf("expected to receive a session ticket within 10 seconds")
	case <-put:
		log.Printf("GET session ticket")
	}

	if *use0RTT {
		log.Printf("0RTT Body:")
		
		if err := roundTripper.Close(); err != nil {
			log.Fatal("Error closing connection")
		}

		defer roundTripper.Close()

		time.Sleep(10 * time.Second)

		url = fmt.Sprintf("https://%s:%s/%s", address, "4444", "index.html")
		urls := []string{url,url,url,url,url}
		wg.Add(len(urls))
		for _, addr := range urls {
			log.Printf("GET %s", addr)
			go func(addr string) {
				now := time.Now()
				//rsp, err := hclient.Get(addr)
				method := http.MethodGet
				if *use0RTT {
					method = http09.MethodGet0RTT
				}
				req, err := http.NewRequest(method, url, nil)
				if err != nil {
					log.Fatal(err)
				}
				
				rsp, err := roundTripper.RoundTrip(req)
				if err != nil {
					log.Fatal(err)
				}
				defer rsp.Body.Close()

				log.Printf("Got response for %s: %#v", addr, rsp)

				if *printData {
					body := &bytes.Buffer{}
					_, err = io.Copy(body, rsp.Body)
					if err != nil {
						log.Fatal(err)
					}
					log.Printf("Request Body:")
					log.Printf("%s", body.Bytes())
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
}

// func downloadFiles(cl http.RoundTripper, urls []string, use0RTT bool) error {
// 	var g errgroup.Group
// 	for _, u := range urls {
// 		url := u
// 		g.Go(func() error {
// 			return downloadFile(cl, url, use0RTT)
// 		})
// 	}
// 	return g.Wait()
// }

// func downloadFile(cl http.RoundTripper, url string, use0RTT bool) error {
// 	method := http.MethodGet
// 	if use0RTT {
// 		method = http09.MethodGet0RTT
// 	}
// 	req, err := http.NewRequest(method, url, nil)
// 	if err != nil {
// 		return err
// 	}
// 	rsp, err := cl.RoundTrip(req)
// 	if err != nil {
// 		return err
// 	}
// 	defer rsp.Body.Close()

// 	file, err := os.Create("/downloads" + req.URL.Path)
// 	if err != nil {
// 		return err
// 	}
// 	defer file.Close()
// 	_, err = io.Copy(file, rsp.Body)
// 	return err
// }