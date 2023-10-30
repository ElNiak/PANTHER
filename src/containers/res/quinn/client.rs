//! This example demonstrates an HTTP client that requests files from a server.
//!
//! Checkout the `README.md` for guidance.

use std::{
    fs,
    io::{self, Write},
    net::ToSocketAddrs,
    path::PathBuf,
    time::{Duration, Instant},
};

use anyhow::{anyhow, Result};
use structopt::StructOpt;
use tracing::{error, info};
use url::Url;
use std::{thread, time};


mod common;
use std::sync::Arc;
use rustls::ServerCertVerified;
use proto::ClientConfig;
// Implementation of `ServerCertVerifier` that verifies everything as trustworthy.
struct SkipCertificationVerification;

impl rustls::ServerCertVerifier for SkipCertificationVerification {
    fn verify_server_cert(
        &self, _: &rustls::RootCertStore, _: &[rustls::Certificate], _: webpki::DNSNameRef, _: &[u8],
    ) -> Result<rustls::ServerCertVerified, rustls::TLSError> {
        Ok(ServerCertVerified::assertion())
    }
}

/// HTTP/0.9 over QUIC client
#[derive(StructOpt, Debug)]
#[structopt(name = "client")]
struct Opt {
    /// Perform NSS-compatible TLS key logging to the file specified in `SSLKEYLOGFILE`.
    #[structopt(long = "keylog")]
    keylog: bool,

    url: Url,

    /// Override hostname used for certificate verification
    #[structopt(long = "host")]
    host: Option<String>,

    /// Custom certificate authority to trust, in DER format
    #[structopt(parse(from_os_str), long = "ca")]
    ca: Option<PathBuf>,

    /// Simulate NAT rebinding after connecting
    #[structopt(long = "rebind")]
    rebind: bool,

     /// Simulate 0rtt rebinding after connecting
    #[structopt(long = "zrtt")]
    zrtt: bool,
}

fn main() {
    tracing::subscriber::set_global_default(
        tracing_subscriber::FmtSubscriber::builder()
            .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
            .finish(),
    )
    .unwrap();
    let opt = Opt::from_args();
    let code = {
        if let Err(e) = run(opt) {
            eprintln!("ERROR: {}", e);
            1
        } else {
            0
        }
    };
    ::std::process::exit(code);
}

#[tokio::main]
async fn run(options: Opt) -> Result<()> {
    let url = options.url;
    let remote = (url.host_str().unwrap(), url.port().unwrap_or(4433))
        .to_socket_addrs()?
        .next()
        .ok_or_else(|| anyhow!("couldn't resolve to an address"))?;

    let zrtt = options.zrtt;

    if zrtt {
        let mut tls_config = rustls::ClientConfig::new();
        tls_config.versions = vec![rustls::ProtocolVersion::TLSv1_3];
        tls_config.enable_early_data = true;
        tls_config
            .dangerous()
            .set_certificate_verifier(Arc::new(SkipCertificationVerification));
        tls_config.alpn_protocols = vec![b"hq-29"[..].into()];
        if options.keylog {
            tls_config.key_log = Arc::new(rustls::KeyLogFile::new());
        }
        let mut transport = quinn::TransportConfig::default();
        transport.send_window(1024 * 1024 * 2);
        transport.receive_window(1024 * 1024 * 2).unwrap();
        transport
            .max_idle_timeout(Some(Duration::from_secs(10)))
            .unwrap();
        let client_config = quinn::ClientConfig {
            crypto: Arc::new(tls_config),
            transport: Arc::new(transport),
        };
        //client_config.protocols(common::ALPN_QUIC_HTTP);
        let mut endpoint = quinn::Endpoint::builder();
        endpoint.default_client_config(client_config.clone());

        let host = options
            .host
            .as_ref()
            .map_or_else(|| url.host_str(), |x| Some(&x))
            .ok_or_else(|| anyhow!("no hostname specified"))?;

        let (endpoint, _) = endpoint.bind(&"[::]:0".parse().unwrap())?;
        let new_conn = endpoint
            .connect(&remote, &host)?
            .await
            .map_err(|e| anyhow!("failed to connect: {}", e))?;
        
        let request = format!("GET {}\r\n", url.path());
        let start = Instant::now();
        let mut i = 0;
        while i < 1 {
            let (mut send, recv) = new_conn
                .connection
                .open_bi()
                .await
                .map_err(|e| anyhow!("failed to open stream: {}", e))?;
            if options.rebind {
                let socket = std::net::UdpSocket::bind("[::]:0").unwrap();
                let addr = socket.local_addr().unwrap();
                eprintln!("rebinding to {}", addr);
                endpoint.rebind(socket).expect("rebind failed");
            }
            send.write_all(request.as_bytes())
                .await
                .map_err(|e| anyhow!("failed to send request: {}", e))?;
            send.finish()
                .await
                .map_err(|e| anyhow!("failed to shutdown stream: {}", e))?;
            let response_start = Instant::now();
            eprintln!("request sent at {:?}", response_start - start);
            let resp = recv
                .read_to_end(usize::max_value())
                .await
                .map_err(|e| anyhow!("failed to read response: {}", e))?;
            let duration = response_start.elapsed();
            eprintln!(
                "response received in {:?} - {} KiB/s",
                duration,
                resp.len() as f32 / (duration_secs(&duration) * 1024.0)
            );
            io::stdout().write_all(&resp).unwrap();
            io::stdout().flush().unwrap();
            i = i + 1;
        }

        new_conn.connection.close(0u32.into(), b"done");

        let ten_millis = time::Duration::from_millis(7000);
        thread::sleep(ten_millis);


        //let saw_cert = Arc::new(Mutex::new(false));
        let quinn::ClientConfig {
            mut crypto,
            transport,
        } = client_config.clone();
        
        Arc::make_mut(&mut crypto)
            .dangerous()
            .set_certificate_verifier(Arc::new(SkipCertificationVerification));
        let client_config = quinn::ClientConfig { crypto, transport };

        let mut url2 = url.clone();
        url2.set_port(Some(4444));
        let remote2 = (url2.host_str().unwrap(), url2.port().unwrap_or(4444))
            .to_socket_addrs()?
            .next()
            .ok_or_else(|| anyhow!("couldn't resolve to an address"))?;

        let conn = match endpoint
            .connect_with(client_config, &remote2, &host)?
            .into_0rtt()
        {
            Ok((new_conn, _)) => {
                let mut j = 0;
                while j < 3 {
                    let (mut send, recv) = new_conn
                        .connection
                        .open_bi()
                        .await
                        .map_err(|e| anyhow!("failed to open stream: {}", e))?;
                    if options.rebind {
                        let socket = std::net::UdpSocket::bind("[::]:0").unwrap();
                        let addr = socket.local_addr().unwrap();
                        eprintln!("rebinding to {}", addr);
                        endpoint.rebind(socket).expect("rebind failed");
                    }
                    send.write_all(request.as_bytes())
                        .await
                        .map_err(|e| anyhow!("failed to send request: {}", e))?;
                    send.finish()
                        .await
                        .map_err(|e| anyhow!("failed to shutdown stream: {}", e))?;
                    let response_start = Instant::now();
                    eprintln!("request sent at {:?}", response_start - start);
                    let resp = recv
                        .read_to_end(usize::max_value())
                        .await
                        .map_err(|e| anyhow!("failed to read response: {}", e))?;
                    let duration = response_start.elapsed();
                    eprintln!(
                        "response received in {:?} - {} KiB/s",
                        duration,
                        resp.len() as f32 / (duration_secs(&duration) * 1024.0)
                    );
                    io::stdout().write_all(&resp).unwrap();
                    io::stdout().flush().unwrap();
                    j = j + 1;
                }
                new_conn.connection
            }
            Err(conn) => {
                info!("0-RTT unsupported");
                let new_conn = conn
                    .await
                    .map_err(|e| anyhow!("failed to connect: {}", e))?;
                new_conn.connection
            }
        };
        conn.close(0u32.into(), b"done");

        endpoint.wait_idle().await;


    } else {
        let mut endpoint = quinn::Endpoint::builder();
        let mut client_config = quinn::ClientConfigBuilder::default();
        client_config.protocols(common::ALPN_QUIC_HTTP);
        if options.keylog {
            client_config.enable_keylog();
        }
        if let Some(ca_path) = options.ca {
            client_config
                .add_certificate_authority(quinn::Certificate::from_der(&fs::read(&ca_path)?)?)?;
        } else {
            let dirs = directories_next::ProjectDirs::from("org", "quinn", "quinn-examples").unwrap();
            match fs::read(dirs.data_local_dir().join("cert.der")) {
                Ok(cert) => {
                    client_config.add_certificate_authority(quinn::Certificate::from_der(&cert)?)?;
                }
                Err(ref e) if e.kind() == io::ErrorKind::NotFound => {
                    info!("local server certificate not found");
                }
                Err(e) => {
                    error!("failed to open local server certificate: {}", e);
                }
            }
        }
        let mut cfg = client_config.build();
        //let client_config_copy = cfg.clone();
    
        // Get a mutable reference to the 'crypto' config in the 'client config'.
        let tls_cfg: &mut rustls::ClientConfig =
            std::sync::Arc::get_mut(&mut cfg.crypto).unwrap();
    
        // Change the certification verifier.
        // This is only available when compiled with the 'dangerous_configuration' feature.
        tls_cfg
            .dangerous()
            .set_certificate_verifier(Arc::new(SkipCertificationVerification));
    
        endpoint.default_client_config(cfg.clone());
    
        let (endpoint, _) = endpoint.bind(&"[::]:0".parse().unwrap())?;
    
        let request = format!("GET {}\r\n", url.path());
        let start = Instant::now();
        let rebind = options.rebind;
        let host = options
            .host
            .as_ref()
            .map_or_else(|| url.host_str(), |x| Some(&x))
            .ok_or_else(|| anyhow!("no hostname specified"))?;
        
        let new_conn = endpoint
            .connect(&remote, &host)?
            .await
            .map_err(|e| anyhow!("failed to connect: {}", e))?;
        eprintln!("connected at {:?}", start.elapsed());

        eprintln!("connecting to {} at {}", host, remote);
        info!("cfg = {:?}",cfg);
   
        let quinn::NewConnection {
            connection: conn, ..
        } = new_conn;
    
        let mut i = 0;
        while i < 10 {
            let (mut send, recv) = conn
                .open_bi()
                .await
                .map_err(|e| anyhow!("failed to open stream: {}", e))?;
            if options.rebind {
                let socket = std::net::UdpSocket::bind("[::]:0").unwrap();
                let addr = socket.local_addr().unwrap();
                eprintln!("rebinding to {}", addr);
                endpoint.rebind(socket).expect("rebind failed");
            }
            send.write_all(request.as_bytes())
                .await
                .map_err(|e| anyhow!("failed to send request: {}", e))?;
            send.finish()
                .await
                .map_err(|e| anyhow!("failed to shutdown stream: {}", e))?;
            let response_start = Instant::now();
            eprintln!("request sent at {:?}", response_start - start);
            let resp = recv
                .read_to_end(usize::max_value())
                .await
                .map_err(|e| anyhow!("failed to read response: {}", e))?;
            let duration = response_start.elapsed();
            eprintln!(
                "response received in {:?} - {} KiB/s",
                duration,
                resp.len() as f32 / (duration_secs(&duration) * 1024.0)
            );
            io::stdout().write_all(&resp).unwrap();
            io::stdout().flush().unwrap();
            i = i + 1;
        }
        conn.close(0u32.into(), b"done");
    
        // Give the server a fair chance to receive the close packet
        endpoint.wait_idle().await;    
    }
    Ok(())
}

fn duration_secs(x: &Duration) -> f32 {
    x.as_secs() as f32 + x.subsec_nanos() as f32 * 1e-9
}

async fn hq_get(stream: (quinn::SendStream, quinn::RecvStream), path: &str) -> Result<Vec<u8>> {
    let (mut send, recv) = stream;
    send.write_all(&format!("GET {}\r\n", path).as_bytes())
        .await
        .map_err(|e| anyhow!("failed to send request: {}", e))?;
    send.finish()
        .await
        .map_err(|e| anyhow!("failed to shutdown stream: {}", e))?;
    let response = recv
        .read_to_end(usize::max_value())
        .await
        .map_err(|e| anyhow!("failed to read response: {}", e))?;
    Ok(response)
}
