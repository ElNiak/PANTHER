//! This example demonstrates an HTTP client that requests files from a server.
//!
//! Checkout the `README.md` for guidance.

use std::{
    fs,
    io::{self, Write},
    net::ToSocketAddrs,
    path::PathBuf,
    sync::Arc,
    time::{Duration, Instant},
};

use anyhow::{anyhow, Result};
use structopt::StructOpt;
use tracing::{error, info};
use url::Url;
use std::{thread, time};

mod common;
struct SkipServerVerification;

impl SkipServerVerification {
    fn new() -> Arc<Self> {
        Arc::new(Self)
    }
}

impl rustls::client::ServerCertVerifier for SkipServerVerification {
    fn verify_server_cert(
        &self,
        _end_entity: &rustls::Certificate,
        _intermediates: &[rustls::Certificate],
        _server_name: &rustls::ServerName,
        _scts: &mut dyn Iterator<Item = &[u8]>,
        _ocsp_response: &[u8],
        _now: std::time::SystemTime,
    ) -> Result<rustls::client::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::ServerCertVerified::assertion())
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
        let mut roots = rustls::RootCertStore::empty();
        if let Some(ca_path) = options.ca {
            roots.add(&rustls::Certificate(fs::read(&ca_path)?))?;
        } else {
            let dirs = directories_next::ProjectDirs::from("org", "quinn", "quinn-examples").unwrap();
            match fs::read(dirs.data_local_dir().join("cert.der")) {
                Ok(cert) => {
                    roots.add(&rustls::Certificate(cert))?;
                }
                Err(ref e) if e.kind() == io::ErrorKind::NotFound => {
                    info!("local server certificate not found");
                }
                Err(e) => {
                    error!("failed to open local server certificate: {}", e);
                }
            }
        }
        let mut client_crypto = rustls::ClientConfig::builder()
            .with_safe_defaults()
            .with_custom_certificate_verifier(SkipServerVerification::new())
            // .with_root_certificates(roots)
            .with_no_client_auth();

        client_crypto.alpn_protocols = common::ALPN_QUIC_HTTP.iter().map(|&x| x.into()).collect();
        if options.keylog {
            client_crypto.key_log = Arc::new(rustls::KeyLogFile::new());
        }

        let mut endpoint = quinn::Endpoint::client("[::]:0".parse().unwrap())?;
        endpoint.set_default_client_config(quinn::ClientConfig::new(Arc::new(client_crypto.clone())));

        let request = format!("GET {}\r\n", url.path());
        let start = Instant::now();
        let rebind = options.rebind;
        let host = options
            .host
            .as_ref()
            .map_or_else(|| url.host_str(), |x| Some(x))
            .ok_or_else(|| anyhow!("no hostname specified"))?;

        eprintln!("connecting to {} at {}", host, remote);
        let new_conn = endpoint
            .connect(remote, host)?
            .await
            .map_err(|e| anyhow!("failed to connect: {}", e))?;
        eprintln!("connected at {:?}", start.elapsed());
        let quinn::NewConnection {
            connection: conn, ..
        } = new_conn;
        let (mut send, recv) = conn
            .open_bi()
            .await
            .map_err(|e| anyhow!("failed to open stream: {}", e))?;
        if rebind {
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
        conn.close(0u32.into(), b"done");

        // Give the server a fair chance to receive the close packet
 
        let ten_millis = time::Duration::from_millis(15000);
        thread::sleep(ten_millis);

        let client_config = quinn::ClientConfig::new(Arc::new(client_crypto.clone()));

        let mut url2 = url.clone();
        url2.set_port(Some(4444));
        let remote2 = (url2.host_str().unwrap(), url2.port().unwrap_or(4433))
            .to_socket_addrs()?
            .next()
            .ok_or_else(|| anyhow!("couldn't resolve to an address"))?;

        let conn = match endpoint
            .connect_with(client_config, remote2, &host)?
            .into_0rtt()
        {
            Ok((new_conn, _)) => {
                let mut j = 0;
                while j < 3 {
                    let (mut send, recv) = new_conn.connection
                        .open_bi()
                        .await
                        .map_err(|e| anyhow!("failed to open stream: {}", e))?;
                    if rebind {
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
        Ok(())
    } else {
        let mut roots = rustls::RootCertStore::empty();
        if let Some(ca_path) = options.ca {
            roots.add(&rustls::Certificate(fs::read(&ca_path)?))?;
        } else {
            let dirs = directories_next::ProjectDirs::from("org", "quinn", "quinn-examples").unwrap();
            match fs::read(dirs.data_local_dir().join("cert.der")) {
                Ok(cert) => {
                    roots.add(&rustls::Certificate(cert))?;
                }
                Err(ref e) if e.kind() == io::ErrorKind::NotFound => {
                    info!("local server certificate not found");
                }
                Err(e) => {
                    error!("failed to open local server certificate: {}", e);
                }
            }
        }
        let mut client_crypto = rustls::ClientConfig::builder()
            .with_safe_defaults()
            .with_custom_certificate_verifier(SkipServerVerification::new())
            // .with_root_certificates(roots)
            .with_no_client_auth();

        client_crypto.alpn_protocols = common::ALPN_QUIC_HTTP.iter().map(|&x| x.into()).collect();
        if options.keylog {
            client_crypto.key_log = Arc::new(rustls::KeyLogFile::new());
        }

        let mut endpoint = quinn::Endpoint::client("[::]:0".parse().unwrap())?;
        endpoint.set_default_client_config(quinn::ClientConfig::new(Arc::new(client_crypto)));

        let request = format!("GET {}\r\n", url.path());
        let start = Instant::now();
        let rebind = options.rebind;
        let host = options
            .host
            .as_ref()
            .map_or_else(|| url.host_str(), |x| Some(x))
            .ok_or_else(|| anyhow!("no hostname specified"))?;

        eprintln!("connecting to {} at {}", host, remote);
        let new_conn = endpoint
            .connect(remote, host)?
            .await
            .map_err(|e| anyhow!("failed to connect: {}", e))?;
        eprintln!("connected at {:?}", start.elapsed());
        let quinn::NewConnection {
            connection: conn, ..
        } = new_conn;

        let mut j = 0;
        while j < 5 {
            let (mut send, recv) = conn
                .open_bi()
                .await
                .map_err(|e| anyhow!("failed to open stream: {}", e))?;
            if rebind {
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
        conn.close(0u32.into(), b"done");

        // Give the server a fair chance to receive the close packet
        endpoint.wait_idle().await;

        Ok(())
    }
}

fn duration_secs(x: &Duration) -> f32 {
    x.as_secs() as f32 + x.subsec_nanos() as f32 * 1e-9
}
