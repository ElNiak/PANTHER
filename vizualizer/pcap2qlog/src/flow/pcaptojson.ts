import {exec, execSync} from "child_process";
import * as path from "path";

export class PCAPToJSON{

    public static async TransformToJSON(pcapPath:string, outputDirectory:string, tsharkLocation: string, secretsPath?:string ):Promise<string> {

        // assumptions:
        // - pcapPath and secretsPath are LOCAL (if it was a URL, it has to be pre-downloaded)
        // - outputDirectory exists

        let output:Promise<string> = new Promise<string>( (resolver, rejecter) => {

            let timeoutMin = 1;

            let randomFilename = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            let outputPath = outputDirectory + path.sep + randomFilename + ".json";


            // if not done after the expected timeout, we will assume the tshark call to hang and proceed
            let timeoutHappened:boolean = false;
            let timer = setTimeout( function(){
                timeoutHappened = true;

                rejecter("Timeout, tshark didn't complete within " + timeoutMin + " minutes");

            }, timeoutMin * 60 * 1000 );

            // /wireshark/run/tshark --no-duplicate-keys -r pcap.pcap -T json -o tls.keylog_file:/srv/secrets.keys > output.json

            //console.log("About to exec tshark");
            let option = "";
            if( secretsPath )
                option = `-o tls.keylog_file:${secretsPath}`;

            //exec( `echo ${pcapPath} > ${outputPath}`, function(error, {}, stderr){
            exec( tsharkLocation + ` --no-duplicate-keys -r ${pcapPath} -T json ${option} > ${outputPath}`, function(error, {}, stderr){
                if( timeoutHappened )
                    return;

                clearTimeout(timer);

                //console.log("Execed tshark");

                if( error ){
                    //console.log("-----------------------------------------");
                    //console.log("TransformToJSON : ERROR : ", error, stderr, pcapPath, outputPath);
                    //console.log("-----------------------------------------");

                    rejecter( "tshark:TransformToJSON : error : " + error );
                }
                else{
                    resolver( outputPath );
                }
            });
        });

        return output;
    }

}