import {exec, execSync} from "child_process";
import * as path from "path";
import { getFileExtension } from "../util/FileUtil";
const URL = require("url").URL;

export class Downloader{

    public static async DownloadIfRemote(inputPath:string, outputDirectory:string):Promise<string> {

        if( inputPath.indexOf("http") >= 0 || inputPath.indexOf("https") >= 0 ){
            //console.log("File is a URL, downloading...", inputPath, outputDirectory );
    
            let randomFilename = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            randomFilename += getFileExtension( inputPath );
            let outputPath:string = outputDirectory + path.sep + randomFilename;
    
            return Downloader.DownloadAsync( inputPath, outputPath );
        }
        else
            return inputPath;

    } 

    public static ValidateRemoteURL(url:string):string {

        if( url === undefined || url === "" ){
            throw new Error("url was empty");
        }

        let validURL = new URL(url); // throws error if not valid remote URL
        
        // URL ctor validator apparently doesn't work 100%, so perform some additional regex magics
        // https://github.com/xxorax/node-shell-escape/blob/master/shell-escape.js
        // https://github.com/ogt/valid-url/blob/master/index.js

        // check invalid characters
        if (/[^a-z0-9\:\/\?\#\|\[\]\@\!\$\&\'\(\)\*\+\,\;\=\.\-\_\~\%]/i.test(url)){
            throw new Error("invalid character present " + url);
        }

        // check for hex escapes that aren't complete
        if (/%[^0-9a-f]/i.test(url)) {
            throw new Error("invalid character present " + url);
        }
        if (/%[0-9a-f](:?[^0-9a-f]|$)/i.test(url))  {
            throw new Error("invalid character present " + url);
        }
        
        // https://stackoverflow.com/questions/49512370/sanitize-user-input-for-child-process-exec-command
        url = url.replace(/(["\s'$`\\])/g,'\\$1');

        return url;
    }

    public static DownloadAsync(inputPath:string, outputPath:string):Promise<string>{

        let output:Promise<string> = new Promise<string>( (resolver, rejecter) => {

            try {
            inputPath = Downloader.ValidateRemoteURL( inputPath );
            }
            catch(e){
                rejecter(e.toString());
            }

            let timeoutMin = 1;
            let wgetLocation:string = "wget"; 
            
            let timeoutHappened:boolean = false;
            let timer = setTimeout( function(){ 
                timeoutHappened = true;
                //console.log("|||||||||||||||||||||||||||||||||||||||||||||");
                //console.log("DownloadAsync : timeout happened, downloading next URL", inputPath );
                //console.log("|||||||||||||||||||||||||||||||||||||||||||||");

                rejecter("Timeout, URL could not be reached within " + timeoutMin + " minutes : " + inputPath);

            }, timeoutMin * 60 * 1000 ); // if not done after the expected timeout, we will assume the wget call to hang and proceed

            exec( wgetLocation + ` --timeout=${timeoutMin} --tries=2 --retry-connrefused -O ${outputPath} ${inputPath}`, function(error, {}, stderr){
                if( timeoutHappened )
                    return;

                clearTimeout(timer);

                if( error ){ 
                    //console.log("-----------------------------------------");    
                    //console.log("DownloadAsync : ERROR : ", error, stderr, inputPath, outputPath);

                    // on error, wget still writes an empty file (or half-downloaded file), which we want to get rid of 
                    let result = execSync( `rm -f ${outputPath}` ); // we assume this will work. If not, nothing we can do about it either way...
                    //console.log(`Removing file ${outputPath} : ${result}`);
                    //console.log("-----------------------------------------"); 

                    rejecter( "DownloadAsync : error : " + inputPath + " : " + error );
                }
                else{
                    resolver( outputPath );
                }
            });
        });

        return output;
    }
}