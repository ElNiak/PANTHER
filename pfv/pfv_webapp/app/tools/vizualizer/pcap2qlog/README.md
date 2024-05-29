# pcap2qlog
A tool to convert .pcap and .pcapng files into qlog files. 

It uses Wireshark's TShark utility under the hood to transform the packet captures to Wireshark's JSON format, which is then transposed to qlog.

# Prerequisites

- git
- wget (when passing in URLs instead of local files)
- NodeJS (v10+)
- Wireshark / TShark version 3.3+ (support for QUIC draft-29+)

Disclaimer: this tool has only been tested on Linux, other operating systems might work but installation and usage can differ from this guide.
For an overview of how we build this tool and Wireshark ourselves, refer to the dockerfiles here: https://github.com/quiclog/qvis-server/blob/master/system/docker_setup

## Installation

Start by cloning the repository to your local machine and entering the cloned directory.

```sh
git clone https://github.com/quiclog/pcap2qlog
cd pcap2qlog
```

Run the following commands to set up the NodeJS project and compile the TypeScript code to JavaScript which can then be run by NodeJS:

```sh
npm install
npx tsc
```

After compiling the TypeScript code, the tool can be executed as follows (assuming you are in the root directory of the project):

```sh
node out/main.js
```

## Options:

```
--tshark=/path/to/tshark, -t /path/to/tshark
        Points the tool to your local installation path of tshark
        Defaults to /wireshark/run/tshark when omitted

--input=/path/to/input.(pcap | .pcapng | json), -i /path/to/input.(pcap | .pcapng | json)
        Path or URL to a single trace in either PCAP, PCAPNG format or JSON format.
        JSON and PCAPNG files are assumed to be decrypted (or containining decryption keys) while PCAP files are assumed to encrypted.
        The --secrets flag should therefore be set separately when passing PCAP files.

--secrets=/path/to/secrets.keys, -s /path/to/secrets
        Path or URL to the secrets file which has to be used to decrypt the PCAP given using the --input flag.

--list=/path/to/list.json, -l /path/to/list.json
        Path to a file containing a list of traces which will converted to a single qlog file.
        The input file should have a structure along the lines of the following:
        {
            "description": "top-level description",
            "paths": [
                { "capture": "https://...", "secrets": "https://...", "description" : "per-file desc" },
                ...
            ]
        }

--output=/path/to/output/directory
        Path to a local output directory where the resulting .qlog will be stored.
        The tool automatically generates a hashed filename for each .qlog file, based on the input path/URL.
        There is currently no option to specify the output filename directly.
        pcap2qlog will write the chosen filename to stdout as its only output so it can be found by other tools calling pcap2qlog. 
```

NOTE: This tool can also be used to merge together multiple (partial) .qlog files. To do this, just pass the files with the --list option.

NOTE: set the PCAPDEBUG environment variable to true (e.g., `PCAPDEBUG=true node out/main.js`) to get debugging output. 

## Examples

```sh
# Using a list of traces
node out/main.js --list=/allinone.json --output=/output_dir --tshark=/path/to/tshark

# TShark is not used if the input is already in the decrypted JSON format
node out/main.js --input=/decrypted.json  --output=/output_dir

# When an encrypted pcap is given, both the secrets file and the tshark executable should be given
node out/main.js --input=/encrypted.pcap --secrets=/secrets.keys  --output=/output_dir --tshark=/path/to/tshark
```