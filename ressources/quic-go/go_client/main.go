package main

import (
	"bytes"
	"strconv"
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
	"sync/atomic"
	quicproxy "github.com/lucas-clemente/quic-go/integrationtests/tools/proxy"
	"github.com/lucas-clemente/quic-go"
	"github.com/lucas-clemente/quic-go/interop/http09"
	//"github.com/lucas-clemente/quic-go/interop/utils"
	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/wire"

	. "github.com/onsi/ginkgo"
	// . "github.com/onsi/ginkgo/extensions/table"
	// . "github.com/onsi/gomega"
	"context"
)

type logger struct {
	enabled bool
}

func (l *logger) Logf(format string, v ...interface{}) {
	if l.enabled {
		log.Printf(format, v...)
	}
}

func scaleDuration(t time.Duration) time.Duration {
	scaleFactor := 1
	if f, err := strconv.Atoi(os.Getenv("TIMESCALE_FACTOR")); err == nil { // parsing "" errors, so this works fine if the env is not set
		scaleFactor = f
	}
	//Expect(scaleFactor).ToNot(BeZero())
	return time.Duration(scaleFactor) * t
}

// func getQuicConfig(conf *quic.Config) *quic.Config {
// 	if conf == nil {
// 		conf = &quic.Config{}
// 	} else {
// 		conf = conf.Clone()
// 	}
// 	if conf.Tracer == nil {
// 		conf.Tracer = quicConfigTracer
// 	} else if quicConfigTracer != nil {
// 		conf.Tracer = logging.NewMultiplexedTracer(quicConfigTracer, conf.Tracer)
// 	}
// 	return conf
// }

func main() {
	verbose := flag.Bool("v", false, "verbose")
	printData := flag.Bool("P", false, "printData the data")
	doVN := flag.Bool("V", false, "version negociation")
	keyLogFile := flag.String("X", "", "key log file")
	sessionFile := flag.String("S", "", "session file")
	//requestSize := flag.Int("G", 50000, "amount of bytes to ask for in the request")
	flag.Bool("R", false, "force RTT connection establishment")

	//secure := flag.Bool("secure", false, "do certificate verification")
	flag.Parse()
	address := flag.Arg(0)
	port := flag.Arg(1)

	logger := &logger{}

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

	
	tlsConfig := &tls.Config{
		RootCAs:            pool,
		InsecureSkipVerify: true,
		KeyLogWriter:       keyLog,
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
			Versions: [] protocol.VersionNumber{}, //0x22334455, 0xff00001d, 0x33445566
			//Tracer:      qlog.NewTracer(getLogWriter),
			//DisablePathMTUDiscovery: true,
		}
	} 
	
	roundTripper := &http09.RoundTripper{
		TLSClientConfig: tlsConfig,
		QuicConfig: quicConf,
	}

	rtt := scaleDuration(5 * time.Millisecond)
	
	runCountingProxy := func(serverPort int) (*quicproxy.QuicProxy, *uint32) {
		var num0RTTPackets uint32 // to be used as an atomic
		proxy, err := quicproxy.NewQuicProxy("localhost:0", &quicproxy.Opts{
			RemoteAddr: fmt.Sprintf("localhost:%d", serverPort),
			DelayPacket: func(_ quicproxy.Direction, data []byte) time.Duration {
				for len(data) > 0 {
					hdr, _, rest, err := wire.ParsePacket(data, 0)
					//Expect(err).ToNot(HaveOccurred())
					if hdr.Type == protocol.PacketType0RTT {
						atomic.AddUint32(&num0RTTPackets, 1)
						break
					}
					data = rest
				}
				return rtt / 2
			},
		})
		//Expect(err).ToNot(HaveOccurred())
		
		return proxy, &num0RTTPackets
	}
		
	dialAndReceiveSessionTicket := func(serverConf *quic.Config) (*tls.Config, *tls.Config) {
		tlsConf := tlsConfig
		if serverConf == nil {
			serverConf = quicConf
			serverConf.Versions = [] protocol.VersionNumber{}
		}
		ln, err := quic.ListenAddrEarly(
			"localhost:0",
			tlsConf,
			serverConf,
		)
		//Expect(err).ToNot(HaveOccurred())
		defer ln.Close()
		
		proxy, err := quicproxy.NewQuicProxy("localhost:0", &quicproxy.Opts{
			RemoteAddr:  fmt.Sprintf("localhost:%d", ln.Addr().(*net.UDPAddr).Port),
			DelayPacket: func(_ quicproxy.Direction, data []byte) time.Duration { return rtt / 2 },
		})
		//Expect(err).ToNot(HaveOccurred())
		defer proxy.Close()
		
		// dial the first session in order to receive a session ticket
		done := make(chan struct{})
		go func() {
			defer GinkgoRecover()
			defer close(done)
			sess, err := ln.Accept(context.Background())
			//Expect(err).ToNot(HaveOccurred())
			<-sess.Context().Done()
		}()
		
		clientConf := quicConf
		gets := make(chan string, 100)
		puts := make(chan string, 100)
		clientConf.ClientSessionCache = newClientSessionCache(gets, puts)
		sess, err := quic.DialAddr(
			fmt.Sprintf("localhost:%d", proxy.LocalPort()),
			clientConf,
			quicConf,
		)
		//Expect(err).ToNot(HaveOccurred())
		//Eventually(puts).Should(Receive())
		// received the session ticket. We're done here.
		//Expect(sess.CloseWithError(0, "")).To(Succeed())
		//Eventually(done).Should(BeClosed())
		return tlsConf, clientConf
	}
		
	transfer0RTTData := func(
		ln quic.EarlyListener,
		proxyPort int,
		clientTLSConf *tls.Config,
		clientConf *quic.Config,
		testdata []byte, // data to transfer
		) {
						// now dial the second session, and use 0-RTT to send some data
		done := make(chan struct{})
		go func() {
			defer GinkgoRecover()
			sess, err := ln.Accept(context.Background())
			//Expect(err).ToNot(HaveOccurred())
			str, err := sess.AcceptUniStream(context.Background())
			//Expect(err).ToNot(HaveOccurred())
			//data, err := io.ReadAll(str)
			//Expect(err).ToNot(HaveOccurred())
			//Expect(data).To(Equal(testdata))
			//Expect(sess.ConnectionState().TLS.Used0RTT).To(BeTrue())
			//Expect(sess.CloseWithError(0, "")).To(Succeed())
			close(done)
		}()
		
		if clientConf == nil {
			clientConf = quicConf
		}
		sess, err := quic.DialAddrEarly(
			fmt.Sprintf("localhost:%d", proxyPort),
			clientTLSConf,
			clientConf,
		)
		//Expect(err).ToNot(HaveOccurred())
		defer sess.CloseWithError(0, "")
		str, err := sess.OpenUniStream()
		//Expect(err).ToNot(HaveOccurred())
		_, err = str.Write(testdata)
		//Expect(err).ToNot(HaveOccurred())
		//Expect(str.Close()).To(Succeed())
		//Expect(sess.ConnectionState().TLS.Used0RTT).To(BeTrue())
		//Eventually(done).Should(BeClosed())
		//Eventually(sess.Context().Done()).Should(BeClosed())
	}
		
	check0RTTRejected := func(
		ln quic.EarlyListener,
		proxyPort int,
		clientConf *tls.Config,
		) {
		sess, err := quic.DialAddrEarly(
			fmt.Sprintf("localhost:%d", proxyPort),
			clientConf,
			quicConf,
		)
		//Expect(err).ToNot(HaveOccurred())
		str, err := sess.OpenUniStream()
		//Expect(err).ToNot(HaveOccurred())
		_, err = str.Write(make([]byte, 3000))
		//Expect(err).ToNot(HaveOccurred())
		//Expect(str.Close()).To(Succeed())
		//Expect(sess.ConnectionState().TLS.Used0RTT).To(BeFalse())
		
		// make sure the server doesn't process the data
		ctx, cancel := context.WithTimeout(context.Background(), scaleDuration(50*time.Millisecond))
		defer cancel()
		serverSess, err := ln.Accept(ctx)
		//Expect(err).ToNot(HaveOccurred())
		//Expect(serverSess.ConnectionState().TLS.Used0RTT).To(BeFalse())
		_, err = serverSess.AcceptUniStream(ctx)
		//Expect(err).To(Equal(context.DeadlineExceeded))
		//Expect(serverSess.CloseWithError(0, "")).To(Succeed())
		//Eventually(sess.Context().Done()).Should(BeClosed())
	}
		
	// can be used to extract 0-RTT from a packetTracer
	get0RTTPackets := func(packets []packet) []protocol.PacketNumber {
		var zeroRTTPackets []protocol.PacketNumber
		for _, p := range packets {
			if p.hdr.Type == protocol.PacketType0RTT {
				zeroRTTPackets = append(zeroRTTPackets, p.hdr.PacketNumber)
			}
		}
		return zeroRTTPackets
	}

	if !*verbose {
		logger.enabled = false
	}
	
	defer roundTripper.Close()
	hclient := &http.Client{
		Transport: roundTripper,
	}

	gets := make(chan string, 100)
	puts := make(chan string, 100)
	hclient.ClientSessionCache = newClientSessionCache(gets, puts)

	var url = fmt.Sprintf("https://%s:%s/%s", address, port, "index.html")
	var wg sync.WaitGroup
	urls := []string{url,url,url,url,urll}
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

type clientSessionCache struct {
	mutex sync.Mutex
	cache map[string]*tls.ClientSessionState

	gets chan<- string
	puts chan<- string
}

func newClientSessionCache(gets, puts chan<- string) *clientSessionCache {
	return &clientSessionCache{
		cache: make(map[string]*tls.ClientSessionState),
		gets:  gets,
		puts:  puts,
	}
}