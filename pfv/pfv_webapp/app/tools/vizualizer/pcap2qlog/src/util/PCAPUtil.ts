
import * as qlog from "@quictools/qlog-schema/dist/draft-01/QLog";

export class PCAPUtil {


    public static getFrameTypeName(frameType: number): qlog.QUICFrameTypeName {
        if (frameType === 0x00)
            return qlog.QUICFrameTypeName.padding;
        else if (frameType === 0x01)
            return qlog.QUICFrameTypeName.ping;
        else if (frameType === 0x02 || frameType === 0x03) // 0x02 is without ECN while 0x03 is with ECN
            return qlog.QUICFrameTypeName.ack;
        else if (frameType === 0x04)
            return qlog.QUICFrameTypeName.reset_stream;
        else if (frameType === 0x05)
            return qlog.QUICFrameTypeName.stop_sending;
        else if (frameType === 0x06)
            return qlog.QUICFrameTypeName.crypto;
        else if (frameType === 0x07)
            return qlog.QUICFrameTypeName.new_token;
        else if (frameType >= 0x08 && frameType <= 0x0f)
            return qlog.QUICFrameTypeName.stream;
        else if (frameType === 0x10)
            return qlog.QUICFrameTypeName.max_data;
        else if (frameType === 0x11)
            return qlog.QUICFrameTypeName.max_stream_data;
        else if (frameType === 0x12 || frameType === 0x013) // 0x12 is bidi while 0x13 is uni
            return qlog.QUICFrameTypeName.max_streams;
        else if (frameType === 0x14)
            return qlog.QUICFrameTypeName.data_blocked;
        else if (frameType === 0x15)
            return qlog.QUICFrameTypeName.stream_data_blocked;
        else if (frameType === 0x16 || frameType === 0x017) // 0x16 is bidi while 0x13 is uni
            return qlog.QUICFrameTypeName.streams_blocked;
        else if (frameType === 0x18)
            return qlog.QUICFrameTypeName.new_connection_id;
        else if (frameType === 0x19)
            return qlog.QUICFrameTypeName.retire_connection_id;
        else if (frameType === 0x1a)
            return qlog.QUICFrameTypeName.path_challenge;
        else if (frameType === 0x1b)
            return qlog.QUICFrameTypeName.path_response;
        else if (frameType === 0x1c || frameType === 0x1d) // 0x1c is QUIC-layer error (or no error) while 0x1d is application layer error
            return qlog.QUICFrameTypeName.connection_close;
        return qlog.QUICFrameTypeName.unknown_frame_type;
    }

    public static extractQUICPackets( entry:any ) {
         // in wireshark, an entry can contain 0, 1 or multiple QUIC packets
         // multiple is always an array, 1 is always a normal object, 0 is a normal object but without useful fields
         if ( Array.isArray(entry) ) {
             return entry;
         }
         else {
             // TODO: now we assume all quic packets are useful, revise once we've seen the contrary (have seen this many times with TCP)
             return [entry];
         }
    }   

    // jsonPath should be marked by / instead of ., because wireshark .jsons often use . inside of keys as well (because... logic)
    // so it's more like xPath
    public static ensurePathExists( jsonPath:string, obj:any, throwError:boolean = true ):boolean {
        let pathElements = jsonPath.split("/");
        let currentObj = obj;
        for ( const el of pathElements ) {
            if ( currentObj[el] === undefined ) {
                let summary = JSON.stringify(currentObj).substr(0,5000);
                if ( throwError ) {
                    throw new Error("ParserPCAP:ensurePathExists : path not found : " + jsonPath + " at " + el + " : " + summary);
                }
                else {
                    return false;
                }
            }

            currentObj = currentObj[el];
        }

        return true;
    }
}