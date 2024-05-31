import { Request, Response } from "express";
const { http, https } = require('follow-redirects');

import * as fs from "fs";
import * as path from "path";
import {promisify} from "util";
const URL = require("url").URL;
const readFileAsync = promisify(fs.readFile);
const writeFileAsync = promisify(fs.writeFile);
const removeFileAsync = promisify(fs.unlink);

import { mkDirByPathSync } from "../util/FileUtil";
import { Pcap2Qlog } from "../util/Pcap2Qlog";

export class FileFetchController {

    /*
    public root(req: Request, res: Response) {
        res.status(200).send({
            message: "GET request successful!! " + req.originalUrl
        });
    }
    */

    public async load(req: Request, res: Response) {
        console.log("/loadfiles ", req.query);

        let validateURL = function(url:string, res: Response):boolean | string {
            if( url === undefined || url === "" ){
                console.error("Empty URL passed. If you're setting file=*.pcap, make sure to set secret= as well!");
                res.status(500).send( { "error": "Empty URL passed. If you're setting file=*.pcap, make sure to set secret= as well! "} );
                return false;
            }

            try{
                let validURL = new URL(url); // the ctor validates the URL.
            }
            catch(e){
                console.error("malformed url requested! ", url, e);
                res.status(500).send( { "error": "Malformed URL import. URL must include http(s):// : " + (e as TypeError).name + " : " + url} );
                return false;
            }

            // URL validator apparently doesn't work 100%, so perform some additional regex magics
            // https://github.com/xxorax/node-shell-escape/blob/master/shell-escape.js
            // https://github.com/ogt/valid-url/blob/master/index.js

            // check invalid characters
            if (/[^a-z0-9\:\/\?\#\|\[\]\@\!\$\&\'\(\)\*\+\,\;\=\.\-\_\~\%]/i.test(url)){
                console.error("invalid character present", url);
                res.status(500).send( { "error": "Invalid URL import. : " + url} );
                return false;
            }

            // check for hex escapes that aren't complete
            if (/%[^0-9a-f]/i.test(url)) {
                console.error("invalid character present", url);
                res.status(500).send( { "error": "Invalid URL import. : " + url} );
                return false;
            }
            if (/%[0-9a-f](:?[^0-9a-f]|$)/i.test(url))  {
                console.error("invalid character present", url);
                res.status(500).send( { "error": "Invalid URL import. : " + url} );
                return false;
            }

            // https://stackoverflow.com/questions/49512370/sanitize-user-input-for-child-process-exec-command
            url = url.replace(/(["\s'$`\\])/g,'\\$1');

            return url;
        }
    
        let validateURLs = function( urls:Array<string>, res: Response):boolean {
            for ( const url of urls ){
                let valid = validateURL( url, res );
                if( !valid ){
                    return false;
                }
            }
    
            return true;
        }

         // to easily test locally and allow external users to address the API
        res.header("Access-Control-Allow-Origin", "*");
        res.header("Content-Type", "application/json");

        // the pcap2qlog programme expects something in this format:
        // (the "description" fields are optional, are filled in with the URLs if not present)
        // (the "capture" files can also be .qlog files themselves if you have them. Then they will just be bundled with the output.)
        // (NOTE: code looks at file extensions naively, that's the reason for the ?.pcap)
        /*
        {
            "description": "Top-level description for the full file. e.g., quic-tracker ngtcp2 28/01/2019",
            "paths": [
                { "capture": "https://quic-tracker.info.ucl.ac.be/traces/20190123/65/pcap?.pcap",
                "secrets": "https://quic-tracker.info.ucl.ac.be/traces/20190123/65/secrets?.keys",
                "description" : "per-file description, e.g., handshake ipv6" },
                { "capture": "https://quic-tracker.info.ucl.ac.be/traces/20190123/61/pcap?.pcap",
                "secrets": "https://quic-tracker.info.ucl.ac.be/traces/20190123/61/secrets?.keys",
                "description" : "per-file description, e.g., HTTP/3 GET" },
                ...
            ]
        }
        */
        // OR we can just pass a single .pcap and .keys file if we only have one
        // So, this server-based API supports 4 options:
        // 0. loadfiles?file=my_file.qlog/.netlog : a directly usable .qlog/.netlog file (can also be .qlog.br, .qlog.brotli, .qlog.gz, .qlog.zip, .qlog.gzip)
        // 1. loadfiles?list=url_to_list.json : a fully formed list in the above format, directly usable
        // 2. loadfiles?file=url_to_file.pcap(ng)&secrets=url_to_keys.keys : single file with (optional) keys
        // 3. loadfiles?file1=url_to_file1.pcap&secrets1=url_to_secrets1.keys&file2=url_to_file2.pcap&secrets2=url_to_secrets2.keys ... : transforms this list into the equivalent of the above
        // options 2. and 3. can also have optional "desc" and "desc1", "desc2", "desc3" etc. parameters to add descriptions

        // TODO: FIXME: pcap2qlog expects urls to have proper extensions (e.g., .pcap, .pcapng, .keys, .json and .qlog)
        // validate for this here and quit early if this is violated 

        let cachePath:string = "/srv/qvis-cache";
        let DEBUG_listContents:string = ""; // FIXME: REMOVE

        let options = [];
        let tempListFilePath:string|undefined = undefined; // only used if we construct a list ourselves (2. and 3.)

        // one of both needs to be set to true, but not both!
        let directDownload = false;
        let pcapToQlogDownload = false;

        let directDownloadURL = "";
        let directDownloadEncoding = undefined;

        if( req.query.list ){
            let validURL = validateURL(req.query.list, res);
            if( !validURL )
                return;


            // 1.
            // pcap2qlog has support built-in for downloading remote list files, so just keep it as-is
            //options.push("--list " + req.query.list);
            options.push("--list");
            options.push(req.query.list);
            DEBUG_listContents = req.query.list;
        }
        else if( req.query.file || req.query.file1 ){
            // 0., 2. and 3.
            // we just view 0. and 2. as a simpler version of 3.
            // we create our own list file in the proper format
            interface ICapture{
                capture:string;
                secrets:string;
                description?:string;
            };

            let captures:Array<ICapture> = [];
            if ( req.query.file ){ // 0. and 2.
                // .qlog files don't need a secrets file
                if( req.query.secrets === undefined && req.query.file.indexOf(".qlog") >= 0 ){
                    let validURLs = validateURLs([req.query.file], res);
                    if( !validURLs )
                        return;
                }
                // neither do .pcapng files
                else if( req.query.secrets === undefined && req.query.file.indexOf(".pcapng") >= 0 ){
                    let validURLs = validateURLs([req.query.file], res);
                    if( !validURLs )
                        return;
                }
                // neither do .netlog files
                else if( req.query.secrets === undefined && req.query.file.indexOf(".netlog") >= 0 ){
                    let validURLs = validateURLs([req.query.file], res);
                    if( !validURLs )
                        return;
                }
                else {
                    let validURLs = validateURLs([req.query.file, req.query.secrets], res);
                    if( !validURLs )
                        return;
                }

                captures.push({ capture: req.query.file, secrets: req.query.secrets, description: req.query.desc });
            }
            else{ // req.query.file1 is set => 3.
                let fileFound:boolean = true;
                let currentFileIndex:number = 1;

                do{
                    let captureURL = req.query["file" + currentFileIndex];
                    let secretsURL = req.query["secrets" + currentFileIndex];

                    if( secretsURL === undefined && captureURL.indexOf(".qlog") >= 0 ){
                        let validURLs = validateURLs([captureURL], res);
                        if( !validURLs )
                            return;
                    }
                    else if( secretsURL === undefined && captureURL.indexOf(".pcapng") >= 0 ){
                        let validURLs = validateURLs([req.query.file], res);
                        if( !validURLs )
                            return;
                    }
                    else {
                        let validURLs = validateURLs([captureURL, secretsURL], res);
                        if( !validURLs )
                            return;
                    }

                    captures.push({ capture: captureURL, secrets: secretsURL, description: req.query["desc" + currentFileIndex] });
                    currentFileIndex += 1;

                    if( !req.query["file" + currentFileIndex] )
                        fileFound = false;

                } while(fileFound);
            }

            // check again for case 0. because we want to do that without pcap2qlog if possible
            const encodingMap:Map<string,string|undefined> = new Map<string,string|undefined>([
                [".qlog", undefined],
                [".qlog.br", "br"],
                [".qlog.brotli", "br"],
                [".qlog.gz", "gzip"],
                [".qlog.gzip", "gzip"],
                [".qlog.zip", "gzip"],
                
                [".netlog", undefined],
                [".netlog.br", "br"],
                [".netlog.brotli", "br"],
                [".netlog.gz", "gzip"],
                [".netlog.gzip", "gzip"],
                [".netlog.zip", "gzip"],
            ]);

            let passToPcapToQlog = true;
            if ( captures.length === 1 && captures[0].secrets === undefined ) {

                for ( let extension of encodingMap.keys() ) {
                    if ( captures[0].capture.indexOf(extension) >= 0 ) {

                        directDownloadEncoding = encodingMap.get( extension );
                        directDownloadURL = captures[0].capture;

                        directDownload = true;
                        passToPcapToQlog = false;

                        break;
                    }
                }
            }

            if( passToPcapToQlog ){
                const captureList = {
                    description: req.query.desc || "Generated " + (new Date().toLocaleString()),
                    paths: captures
                }

                const captureString:string = JSON.stringify(captureList, null, 4);
                DEBUG_listContents = captureString;

                // create a temporary file, can be removed later 
                let tempDirectory = path.resolve( cachePath + path.sep + "inputs" );
                mkDirByPathSync( tempDirectory );

                const tempFilename = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15) + ".json";

                try{
                    tempListFilePath = tempDirectory + path.sep + tempFilename;
                    await writeFileAsync( tempListFilePath, captureString );
                    //options.push("--list " + tempListFilePath );
                    options.push("--list");
                    options.push(tempListFilePath);
                }
                catch(e){
                    res.status(500).send( { "error": "Something went wrong writing the list.json file : " + e } );
                    return;
                }

                pcapToQlogDownload = true;
            }
        }
        else{
            res.status(400).send( { "error": "no valid query parameters set. Please use list, file or filex. See github.com/quiclog/qvis-server for more information."} );
            return;
        }

        if ( directDownload ) {

            // trying to just play a proxy because we should be able to just stream the file down. This is pure CORS-avoidance mode
            console.log("Direct proxy for file", directDownloadURL, directDownloadEncoding ? directDownloadEncoding : "");

            if ( directDownloadEncoding ) {
                res.header("Content-Encoding", directDownloadEncoding);
            }

            const parsedDownloadURL = new URL(directDownloadURL);

            let newHeaders = JSON.parse( JSON.stringify(req.headers) ); // poor man's deep copy
            if ( newHeaders.host ) {
                delete newHeaders.host;
            }
            if ( newHeaders.hostname ) {
                delete newHeaders.hostname;
            }

            // we're trying to bypass CORS here, so remove these
            if ( newHeaders["sec-fetch-site"] ) {
                delete newHeaders["sec-fetch-site"];
            }
            if ( newHeaders["sec-fetch-mode"] ) {
                delete newHeaders["sec-fetch-mode"]; 
            }
            if ( newHeaders["sec-fetch-dest"] ) {
                delete newHeaders["sec-fetch-dest"]; 
            }
            if ( newHeaders["sec-fetch-user"] ) {
                delete newHeaders["sec-fetch-user"]; 
            }

            const fetchFromOriginOptions = {
                host: parsedDownloadURL.host,
                // port: parsedDownloadURL.port,
                path: parsedDownloadURL.pathname + parsedDownloadURL.search,
                searchParams: parsedDownloadURL.searchParams, // doesn't work in earlier node versions
                method: req.method,
                headers: newHeaders
            };

            console.log("Proxying directly: ", fetchFromOriginOptions);

            // https://stackoverflow.com/questions/11944932/how-to-download-a-file-with-node-js-without-using-third-party-libraries
            // https://stackoverflow.com/questions/20351637/how-to-create-a-simple-http-proxy-in-node-js

            try {
                if ( directDownloadURL.startsWith("https") ) {

                    const proxy = https.request(fetchFromOriginOptions, (originResponse:any) => {
                        // console.log("Got proxied response back! piping to frontend now!", originResponse.headers);

                        // headers will merge with + overwrite doubles the ones we already set
                        // shouldn't matter for Content-Encoding (if origin doesn't set these, we do above)
                        // also shouldn't matter for Content-Type or CORS headers
                        
                        res.writeHead( originResponse.statusCode, originResponse.headers );
                        
                        originResponse.pipe( res, { end: true });
                    })
                    .on('error', (err:any) => {
                        res.status(500).send( { "error": "Something went wrong fetching the files from the origin server through the qvis CORS proxy : " + err, "url": directDownloadURL, "options": fetchFromOriginOptions } );
                    });

                    req.pipe( proxy, { end: true }); // without this, the proxy request doesn't fire 
                }
                else if ( directDownloadURL.startsWith("http") ) {

                    if ( newHeaders["upgrade-insecure-requests"] ){
                        delete newHeaders["upgrade-insecure-requests"];
                    }

                    const proxy = http.request(fetchFromOriginOptions, (originResponse:any) => {
                        res.writeHead( originResponse.statusCode, originResponse.headers );
                        
                        originResponse.pipe( res, { end: true });
                    })
                    .on('error', (err:any) => {
                        res.status(500).send( { "error": "Something went wrong fetching the files from the origin server through the qvis CORS proxy : " + err, "url": directDownloadURL, "options": fetchFromOriginOptions } );
                    });

                    req.pipe( proxy, { end: true }); // without this, the proxy request doesn't fire 
                }
                else {
                    throw new Error("Unsupported protocol " + directDownloadURL);
                }
            }
            catch(err) {
                res.status(500).send( { "error": "Something went wrong fetching the files from the origin server through the qvis CORS proxy (catch) : " + err, "url": directDownloadURL, "options": fetchFromOriginOptions } );
                return;
            }


            // res.status(200).send( { qlog: jsonContents, debug_list: DEBUG_listContents } );
        }
        else if ( pcapToQlogDownload ) {
            // we need to do more than just stream the file (e.g., combine multiple files, transform pcaps into qlog, etc.)
            // for this, we pass to the pcap2qlog tool

            //options.push("--output " + cachePath);
            options.push("--output");
            options.push(cachePath);

            try{
                let fileName:string = await Pcap2Qlog.Transform(options);
                console.log("Sending back after pcap2qlog: ", fileName);
                //fileName = "/srv/qvis-cache/cache/9ad6e575fae6fe2295ea249a52379cfa8c2552fd_real.qlog"; // FIXME: REMOVE : ONLY FOR DEBUG!
                let fileContents:Buffer = await readFileAsync( fileName );

                if( tempListFilePath ){
                    try{
                        await removeFileAsync( tempListFilePath );
                    }
                    catch(e){
                        // now this is interesting... it's an error but the user won't really care
                        // this only has an impact on our hard disk space
                        // so... for now just ignore and continue
                        console.error("FileFetchController:loadFiles : could not remove temporary list file ", tempListFilePath, e);
                    }
                }
                
                let jsonContents = JSON.parse( fileContents.toString() );
                res.status(200).send( { qlog: jsonContents, debug_list: DEBUG_listContents } );
            }
            catch(e){
                res.status(500).send( { "error": "Something went wrong converting the files to qlog : " + e } );
                return;
            }
        }


        //let fileContents:Buffer = await readFileAsync("/srv/qvis-cache/cache/9ad6e575fae6fe2295ea249a52379cfa8c2552fd_real.qlog");
    }
}

export const fileFetchController = new FileFetchController();
