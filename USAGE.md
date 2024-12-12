# :computer: Usage



## :book: Tests parameters



*Global parameters:*

| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--dir`                | Output directory to create                                                                                | `temp/`                 |
| `--build_dir`          | Build directory to create                                                                                 | `build/`                |
| `--tests_dir`          | Tests directory to create                                                                                 | `build/`                |
| `--iter`               | Number of iterations per test                                                                             | `1`                     |
| `--internal_iteration` | Number of Ivy iterations per test                                                                         | `100`                   |
| `--getstats`           | Print all stats                                                                                           | `True`                  |
| `--compile`            | Compile Ivy tests                                                                                         | `True`                  |
| `--run`                | Launch or not the tested implementation                                                                   | `True`                  |
| `--timeout`            | Timeout                                                                                                   | `100 sec`               |
| `--keep_alive`         | Keep alive Ivy implementation                                                                             | `False`                 |
| `--update_ivy`         | Update `<include>` folder for picoTLS files of Ivy (defined by g++)                                       | `True`                  |
| `--docker`             | Use docker                                                                                                | `True`                  |
| `--gperf`              | gperf                                                                                                     | `False`                 |
| `--gdb`                | Use gdb to debug                                                                                          | `False`                 |
| `--memprof`            | Perform memory profiling                                                                                  | `False`                 |
| `--localhost`          | Use localhost network                                                                                     | `True`                  |
| `--vnet`               | Use virtual network                                                                                       | `False`                 |
| `--shadow`             | Use Shadow simulator                                                                                      | `False`                 |
| `--webapp`             | WebApp UI                                                                                                 | `False`                 |
| `--worker`             | Worker server mode                                                                                        | `False`                 |

*Simulator parameters:*

| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--loss`               | Shadow: loss percentage                                                                                   | `0`                     |
| `--jitter`             | Shadow: jitter in milliseconds                                                                            | `10`                    |
| `--latency`            | Shadow: latency in milliseconds                                                                           | `10`                    |

*QUIC parameters:*

| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--nb_request`         | Number of request send by implementations (not always possible)                                           | `10`                    |
| `--initial_version`    | Initial version for protocol testing                                                                      | `1`                     |
| `--nclient`            | Number of clients per test for server implementation                                                      | `1`                     |
| `--alpn`               | Application-Layer Protocol Negotiation options                                                            | `hq-interop`, `hq-29`, `hq-28` |
