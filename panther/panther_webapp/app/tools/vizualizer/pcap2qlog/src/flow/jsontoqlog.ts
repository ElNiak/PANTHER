
import * as fs from "fs";
import {promisify} from "util";
import {ParserPCAP} from "../parsers/ParserPCAP";
import * as qlog from "@quictools/qlog-schema";


const readFileAsync = promisify(fs.readFile);
const writeFileAsync = promisify(fs.writeFile);

export class JSONToQLog{

    public static async TransformToQLog(jsonPath:string, outputDirectory:string,  originalFile: string, logRawPayloads: boolean, secretsPath?:string, logUnknownFramesFields: boolean = false):Promise<qlog.IQLog> {

        // assumptions:
        // - jsonPath and secretsPath are LOCAL (if it was a URL, it has to be pre-downloaded)
        // - the .json file is the DECRYPTED output of tshark when run on a .pcap or .pcapng
        // - outputDirectory exists

        let fileContents:Buffer = await readFileAsync(jsonPath);
        let jsonContents:any = JSON.parse( fileContents.toString() );

        let secretsContents:any = undefined;
        if( secretsPath ){
            let secretsFileContents:Buffer = await readFileAsync(secretsPath);
            // TODO :parse the secrets
            secretsContents = secretsFileContents.toString();
        }


        // TODO: properly deal with different versions of QUIC and address the correct parser
        // see how we did this in @quictools/qlog-schema and replicate something similar here
        let qlog:qlog.IQLog = ParserPCAP.Parse( jsonContents, originalFile, logRawPayloads, secretsContents, logUnknownFramesFields );

        // we could write this to file directly now
        // BUT we want to aggregate possible different IQLogs together in 1 combined/grouped IQLog before writing the final output
        // so we return the QLog instead of writing, so the caller can decide what to do
        // (otherwhise we would write here and have to re-read again later, which isn't very efficient)

        return qlog;
    }
}