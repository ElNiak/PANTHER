import {exec} from "child_process";
import {spawn} from "child_process";

export class Pcap2Qlog {

    public static async Transform(options:Array<string>) : Promise<string> {

        let output:Promise<string> = new Promise<string>( (resolver, rejecter) => {

            // if not done after the expected timeout, we will assume the tshark call to hang and proceed
            const timeoutMin:number = 1;
            let timeoutHappened:boolean = false;
            let timer = setTimeout( function(){ 
                timeoutHappened = true;

                rejecter("Timeout, pcap2qlog didn't complete within " + timeoutMin + " minutes");

            }, timeoutMin * 60 * 1000 ); // 1 minute

            let pcap2qlogLocation = "/srv/pcap2qlog/out/main.js";
            //let pcap2qlogLocation = "/home/rmarx/WORK/QUICLOG/pcap-to-qlog/trunk/out/main.js";
            options.unshift(pcap2qlogLocation);

            console.log("Running pcap2qlog " + options.join(" "));

            // use spawn instead of exec() for added security https://stackoverflow.com/a/50424976
            const pcap2qlog = spawn('node', options);

            let outputFilePath:string|undefined = undefined;
            let error:string|undefined = undefined;

            pcap2qlog.stdout.on('data', (data) => {
                //console.log(`stdout: ${data}`);
                outputFilePath = data.toString();
            });

            pcap2qlog.stderr.on('data', (data) => {
                //console.log(`stderr: ${data}`);
                error = data.toString();
            });

            // pcap2qlog.on('close', (code) => {
            //     console.log(`child process closed with code ${code}`);
            // });

            pcap2qlog.on('exit', (code) => {
                if( timeoutHappened ) 
                    return;
                clearTimeout(timer);

                if ( error !== undefined ){
                    console.error("Pcap2Qlog : error : " + error);
                    rejecter( "Pcap2Qlog : error : " + error );
                }
                else {
                    if ( code !== 0 ){
                        console.error("Pcap2Qlog : unknown error, but exit code was not 0! : " + code + " // " + outputFilePath);
                        rejecter( "Pcap2Qlog : unknown error, but exit code was not 0! : " + code + " // " + outputFilePath );
                    }
                    else if( outputFilePath === undefined || outputFilePath === "" ){
                        console.error("Pcap2Qlog : unknown error, but no qlog file written! : " + code);
                        rejecter( "Pcap2Qlog : unknown error, but no qlog file written! : " + code );
                    }
                    else {
                        resolver( outputFilePath.trim() );
                    }
                }
            });

            pcap2qlog.on('error', (err) => {
                if( timeoutHappened ) 
                    return;
                clearTimeout(timer);

                console.log('Failed to start pcap2qlog.', err);
                error += JSON.stringify(err);
                rejecter( "Pcap2Qlog : error : " + error );
            });

            //exec( `echo ${options[0].replace("--list=", "").trim()}`, function(error, stdout, stderr){
            // exec( pcap2qlogLocation + " " + options.join(" "), function(error, stdout, stderr){
            //     if( timeoutHappened ) 
            //         return;

            //     clearTimeout(timer);

            //     //console.log("Execed tshark");

            //     if( error ){ 
            //         //console.log("-----------------------------------------");    
            //         //console.log("TransformToJSON : ERROR : ", error, stderr, pcapPath, outputPath);
            //         //console.log("-----------------------------------------"); 

            //         rejecter( "Pcap2Qlog : error : " + error );
            //     }
            //     else{
            //         resolver( stdout.toString().trim() );
            //     }
            // });
        });

        return output;
    }
}