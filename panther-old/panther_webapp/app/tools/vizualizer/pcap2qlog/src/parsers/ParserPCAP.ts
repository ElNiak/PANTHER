import * as qlog from "@quictools/qlog-schema";
import {PCAPUtil} from "../util/PCAPUtil";
import { VantagePointType, EventField, EventCategory, TransportEventType, QuicFrame, QUICFrameTypeName, IAckFrame, IPaddingFrame, IPingFrame, IResetStreamFrame, IStopSendingFrame, ICryptoFrame, IStreamFrame, INewTokenFrame, IUnknownFrame, IMaxStreamDataFrame, IMaxStreamsFrame, IMaxDataFrame, IDataBlockedFrame, IStreamDataBlockedFrame, IStreamsBlockedFrame, INewConnectionIDFrame, IRetireConnectionIDFrame, IPathChallengeFrame, IPathResponseFrame, IConnectionCloseFrame, ErrorSpace, TransportError, ApplicationError, ConnectivityEventType, IEventSpinBitUpdated, IEventPacket, IEventPacketSent, ConnectionState, IEventTransportParametersSet, IEventConnectionStateUpdated, IDefaultEventFieldNames, CryptoError, PacketType } from "@quictools/qlog-schema";
import { pathToFileURL } from "url";

interface TraceWrapper {
    qlogTrace:qlog.ITrace,

    referenceTime:number,
    currentTime:number,
    trailingEvents: EventField[][],

    currentClientCID:string|undefined, // DCID the server will use to send to the client
    currentServerCID:string|undefined, // DCID the client will use to send to the server

    clientIssuedCIDs:Array<string>,
    serverIssuedCIDs:Array<string>,

    spinbit:boolean,

    currentVersion: string,
    selectedALPN: string|undefined
}

export class ParserPCAP {
        public clientCID: string|undefined = ParserPCAP.DEFAULT_SCID;
        public clientPermittedCIDs: Set<string> = new Set<string>(); // New connection ids the client is permitted to use, communicated using NEW_CONNECTION_ID frames from server to client
        public serverCID: string|undefined = ParserPCAP.DEFAULT_SCID;
        public serverPermittedCIDs: Set<string> = new Set<string>(); // New connection ids the server is permitted to use, communicated using NEW_CONNECTION_ID frames from client to server
        public ODCID: string|undefined = "ODCID_DEFAULT"; // Original destination conn id
        public serverCIDChanged: boolean = false;; // Flip after initial change

        protected traceMap:Map<string, TraceWrapper> = new Map<string, TraceWrapper>(); // maps ODCIDs to a trace
        protected CIDToODCIDMap:Map<string, string> = new Map<string, string>(); // maps actual CIDs to an ODCID (to be used to lookup the trace)

        protected jsonRoot:any = undefined;
        protected originalFileURI:string = "";
        protected debugging:boolean = false;
        protected logUnknownFramesFields:boolean = false;

        private static DEFAULT_SCID = "zerolength:scid";
        private static DEFAULT_DCID = "zerolength:dcid";

        public static Parse(jsonContents:any, originalFile: string, logRawPayloads: boolean, secretsContents:any, logUnknownFramesFields: boolean = false):qlog.IQLog {
            
            let debugging:boolean = process.env.PCAPDEBUG !== undefined; // run: sudo PCAPDEBUG=true node out/main.js ...   (TODO: make this proper, app-wide instead of checking env directly here, which is dirty)

            try {
                let pcapParser = new ParserPCAP( jsonContents, originalFile, debugging, logUnknownFramesFields );

                return pcapParser.parse();
            }
            catch(e) {
                if ( debugging ) {
                    console.log("ParserPCAP: Error occured", e);
                }

                throw e;
            }
        }

        constructor(private jsonTrace: any, originalFile: string, debugging: boolean = false, logUnknownFramesFields: boolean = false) {
            this.debugging = debugging;
            this.jsonRoot = jsonTrace;
            this.originalFileURI = originalFile;
            this.logUnknownFramesFields = logUnknownFramesFields
        }


        private parse():qlog.IQLog {

            let output: qlog.IQLog;

            let debug_totalPacketcount: number = 0;
            let debug_totalQuicPacketcount: number = 0;
            
            // 1. loop over all packets
            // 2. if you find a QUIC packet
            //      2.1 parse its header
            //      2.2 find its trace and create a new trace if it didn't exist yet
            //      2.3 check if global state is updated (e.g., spinbit, version, etc.)
            //      2.4 parse packet frame contents
            //      2.5 add it to the trace

            // 1.
            let debug_packetCount = 0;
            for ( const rawEntry of this.jsonRoot ) {
                ++debug_totalPacketcount;

                if ( !PCAPUtil.ensurePathExists("_source/layers/quic", rawEntry, false) ) {
                    continue;
                }

                // 2.
                // entry can contain 1 or more QUIC packets (e.g., coalescing)
                // TODO: here, we assume [0] will be the initial with the needed data, but in weird cases, could be the 0-RTT one is first... too bad for now 
                const rawPackets = PCAPUtil.extractQUICPackets(rawEntry["_source"]["layers"]["quic"]);
                if ( !rawPackets || rawPackets.length === 0 ) {
                    this.exit("ParserPCAP: invalid QUIC packet found in this pcap", rawPackets);
                }

                if ( this.debugging && (debug_packetCount % 100 === 0 || debug_packetCount === this.jsonRoot.length - 1) ) {
                    console.log("Processing rawEntry ", debug_packetCount);
                }
                ++debug_packetCount;

                for ( const rawPacket of rawPackets ) {

                    // 2.1
                    const packetInfo:{ packetType:qlog.PacketType, header:qlog.IPacketHeader|undefined } = this.convertPacketHeader( rawPacket );
                    if ( packetInfo.packetType === qlog.PacketType.unknown && packetInfo.header === undefined ) {
                        // padding/garbage packet, skipping
                        continue;
                    }

                    const parsedHeader = packetInfo.header!;

                    // check if a CID was zero length and we need to fall back to IP-based shenanigans... rough
                    if ( parsedHeader.scid === ParserPCAP.DEFAULT_SCID) {
                        parsedHeader.scid = this.IPtoCID( true, rawEntry );
                    }
                    if ( parsedHeader.dcid === ParserPCAP.DEFAULT_DCID ) {
                        parsedHeader.dcid = this.IPtoCID( false, rawEntry );
                    }

                    // 2.2
                    let trace:TraceWrapper|undefined = this.getTrace( parsedHeader );
                    if ( trace === undefined ) {
                        if ( packetInfo.packetType === qlog.PacketType.initial ) {

                            let rawFrames = rawPacket["quic.frame"];
                            if ( !Array.isArray(rawFrames) ) {
                                rawFrames = [ rawFrames ];
                            }

                            let foundCryptoFrame = undefined;
                            for ( const rawFrame of rawFrames ) {
                                if ( PCAPUtil.ensurePathExists("tls.handshake/tls.handshake.type", rawFrame, false ) ) {
                                    foundCryptoFrame = rawFrame;
                                    break;
                                }
                            }

                            if ( foundCryptoFrame === undefined ) {
                                this.exit("ParserPCAP: no tls info known for the first QUIC initial, not supported! Are you sure the trace decrypted?", rawPacket, rawPacket["quic.frame"] );
                            }
                            else {
                                if ( foundCryptoFrame["tls.handshake"]["tls.handshake.type"] !== "1" ){ // 1 === ClientHello. 2 === ServerHello
                                    this.exit("ParserPCAP: first QUIC initial in this trace is ServerHello. Pcap2qlog needs the ClientHello to work properly.", rawPackets);
                                }
                                else {
                                    trace = this.addTrace( rawEntry, parsedHeader );
                                }
                            }
                        }
                        else {
                            // this.exit("ParserPCAP: trace doesn't start with the first initial, not yet supported. Abandoning", packetInfo.packetType, packetInfo.header, this.CIDToODCIDMap );

                            if ( this.debugging ) {
                                console.log("ParserPCAP: trace doesn't start with the first initial, not yet supported. Dropping packet.", packetInfo.packetType, packetInfo.header, this.CIDToODCIDMap );
                            }

                            continue;
                        }
                    }

                    // need to keep track of CIDs during connection setup (client-side is done in :addTrace, this is for the server-side)
                    if ( packetInfo.packetType === qlog.PacketType.initial ) {
                        // TODO: add check if it's actually from the server side? isn't this implied though? for the client-side, we already add the scid to the map in :addTrace
                        // if we have an initial from the server to the client, we might not have added the server SCID to our lookup map
                        if ( !this.CIDToODCIDMap.has(parsedHeader.scid!) ) {
                            const odcid = this.CIDToODCIDMap.get( parsedHeader.dcid! );
                            if ( odcid !== undefined ) {

                                if ( trace!.currentServerCID !== undefined ) {
                                    this.exit("ParserPCAP: trace already had a serverCID set and sees another initial with a new CID... shouldn't happen!");
                                }

                                if ( this.debugging ) {
                                    console.log("ParserPCAP: adding server scid to CID map: ", parsedHeader.scid, odcid);
                                }
                                this.CIDToODCIDMap.set( parsedHeader.scid!, odcid ); // scid here is the server-chosen CID in the server's initial 

                                trace!.currentServerCID = parsedHeader.scid!;
                            }
                            else {
                                this.exit("ParserPCAP: trying to add the second CID indirection (server -> client) but couldn't find the ODCID!", parsedHeader );
                            }
                        }
                    }

                    const rawFrame = rawEntry["_source"]["layers"]["frame"];
                    const time = this.getTime( rawFrame );
                    trace!.currentTime = Math.round( (time - trace!.referenceTime) * 1000 ); // relative to the trace's first timestamp. Time is in nanoseconds

                    // 2.3
                    this.checkVersionUpdate( trace!, parsedHeader );
                    this.checkSpinBitUpdate( trace!, rawPacket    );
                    if ( trace!.currentServerCID !== undefined ) { // if undefined, we've not yet seen the ServerHello and CID cannot change
                        this.checkCIDUpdate(     trace!, parsedHeader ); // if we started using a new CID issued by NEW_CID frames
                    }

                    // 2.4
                    // we work from the perspective of the client
                    let transportEventType: TransportEventType = TransportEventType.packet_received;
                    if ( this.sentByClient( trace!, parsedHeader ) ) {
                        transportEventType = TransportEventType.packet_sent;
                    }

                    const evtData: IEventPacket = {
                        packet_type: packetInfo.packetType,
                        header: packetInfo.header!,
                    };

                    const frames = this.extractFrames( trace!, rawPacket );
                    evtData.frames = frames;

                    // used to be: this.addNewCID(dcid, frame.connection_id);
                    this.updateCIDsFromFrames( trace!, parsedHeader, frames ); // link NEW_CID frames to internal Trace state so we can bind packets to the correct trace


                    // 2.4
                    this.addEvent(trace!, [
                        "" + trace!.currentTime,
                        EventCategory.transport,
                        transportEventType,
                        evtData
                    ]);
                
                } // done processing single QUIC packet

            } // done processing raw JSON entry

            const traces = [];
            for ( const wrapper of this.traceMap.values() ) {
                traces.push( wrapper.qlogTrace );
            }

            output = {
                qlog_version: "draft-02-wip",
                title: "" + this.originalFileURI,
                description: "qlog converted from " + this.originalFileURI,
                traces: traces
            };

            if ( this.debugging ) {
                console.log("Found packets: ", debug_totalPacketcount);
                console.log("Of which QUIC: ", debug_totalPacketcount);
                console.log("Split over traces: ", this.traceMap.size);
            }

            return output!;
        }


        protected getTrace( packetHeader:qlog.IPacketHeader ):TraceWrapper | undefined {
            let odcid = this.CIDToODCIDMap.get( "" + packetHeader.dcid );

            if ( odcid ) {
                const trace = this.traceMap.get( odcid );
                if ( !trace ) {
                    this.exit( "getTrace: ODCID was found, but no trace was coupled!", odcid );
                }
                else {
                    return trace;
                }
            }
            else {
                return undefined; // haven't seen this connection before. Should be followed up with a call to addTrace to add it
            }
        }

        // packet MUST be a client-side initial (TLS ClientHello) to work properly 
        protected addTrace( firstRawEntry:any, firstPacketHeader:qlog.IPacketHeader ):TraceWrapper {

            let odcid = firstPacketHeader.dcid;
            this.CIDToODCIDMap.set( odcid!, odcid! );
            this.CIDToODCIDMap.set( firstPacketHeader.scid!, odcid! ); // the first packet's source cid from te client becomes the server's dcid from then on

            if ( this.debugging ) {
                console.log("ParserPCAP: adding new trace: ODCID ", odcid, " from client scid", firstPacketHeader.scid);
            }

            const traceNr = this.traceMap.size + 1;

            const referenceTime = this.getTime(firstRawEntry["_source"]["layers"]["frame"]);

            const trace:qlog.ITrace = {
                title: "Connection " + traceNr,
                description: "Connection " + traceNr + " in qlog from pcap " + this.originalFileURI,
                vantage_point: {
                    name: "pcap",
                    type: VantagePointType.network,
                    flow: VantagePointType.client, // Perspective from which the trace is made, e.g. packet_sent from flow=client means that the client has sent a packet while packet_sent from flow=server means that the server sent it.
                },
                configuration: {
                    time_offset: "0",
                    time_units: "ms",
                    original_uris: [ this.originalFileURI ],
                },
                common_fields: {
                    group_id: odcid, // Original destination connection id
                    protocol_type: "QUIC",
                    reference_time: "" + referenceTime
                },
                event_fields: [IDefaultEventFieldNames.relative_time, IDefaultEventFieldNames.category, IDefaultEventFieldNames.event, IDefaultEventFieldNames.data],
                events: []
            };

            const wrapper:TraceWrapper = {
                qlogTrace: trace,
                referenceTime: referenceTime,
                currentTime: referenceTime,
                trailingEvents: [],

                currentClientCID: firstPacketHeader.scid,
                currentServerCID: undefined, // will only know this once the server sends its initial

                clientIssuedCIDs: [],
                serverIssuedCIDs: [],

                spinbit: false,
                currentVersion: "unknown",
                selectedALPN: undefined
            }

            this.traceMap.set( odcid!, wrapper );

            // First event = new connection
            this.addEvent(wrapper, [
                "0",
                qlog.EventCategory.connectivity,
                qlog.ConnectivityEventType.connection_started,
                this.getConnectionInfo(firstRawEntry, firstPacketHeader) as qlog.IEventConnectionStarted,
            ]);

            return wrapper;
        }

        protected sentByClient( trace:TraceWrapper, header:qlog.IPacketHeader ) {
            if ( header.dcid === trace.currentClientCID ) { // currentClientCID is the DCID used by the server to send to the client. So if they are equal, means the server was sending here.
                return false;
            }
            else {
                return true;
            }
        }

        protected exit(message:string, ...args:Array<any> ) {
            if ( this.debugging ) {
                console.log( message, args );
            }

            let argString = "";
            if ( args && args.length > 0 ) {
                argString = " : " + args.reduce((previous:any, current:any) => {
                    return previous + ", " + JSON.stringify(current);
                });
            }

            throw new Error(message + argString);
        }

        

        // Adds an event to the list of events
        // Also appends all trailing events immediately after the new event (see addTrailingEvents() function for more details)
        protected addEvent(trace:TraceWrapper, event: EventField[]) {
            trace.qlogTrace.events.push(event);
            trace.qlogTrace.events = trace.qlogTrace.events.concat(trace.trailingEvents);
            trace.trailingEvents = [];
        }

        // Adds an event to a queue which will be added to the event list after the next main event
        // Uses:
        //  Say we have a connection close event and a packet received event containing the connection close frame
        //  The logical order to log these events is to log the packet received event before the connection close event
        //  This is however not always easy as the connection close event is discovered before the packet received event is fully completed
        // Therefore one is able to queue the connection close event first by calling addTrailingEvent(connectionCloseEvent) first when the connection close frame is discovered and later calling addEvent(packetReceivedEvent) when the packet received event is ready while still maintaining the expected order of events
        protected addTrailingEvent(trace:TraceWrapper, event: EventField[]) {
            trace.trailingEvents.push(event);
        }

        protected IPtoCID( source:boolean, rawEntry:any ) {
            let IP = rawEntry._source.layers.ip;
            let IPsrcField = "ip.src";
            let IPdstField = "ip.dst";
            if ( !IP ) {
                IP = rawEntry._source.layers.ipv6;
                IPsrcField = "ipv6.src";
                IPdstField = "ipv6.dst";
            }

            let UDP = rawEntry._source.layers.udp;

            if ( !UDP ) {
                // sometimes, the UDP stuff is inside an ICMP object (don't ask me why... I don't know)
                UDP = rawEntry._source.layers.icmp.udp;
                if ( !UDP ) {
                    this.exit("ParserPCAP:IPtoCID: no UDP layer found for this QUIC packet, shouldn't happen!", rawEntry);
                }
            }

            let output = "zerolengthCID:";

            if ( source ) {
                output += IP[ IPsrcField ] + ":" + UDP["udp.srcport"];
            }
            else {
                output += IP[ IPdstField ] + ":" + UDP["udp.dstport"]; 
            }

            return output;
        }

        protected checkSpinBitUpdate( trace:TraceWrapper, rawPacket:any ) {
            
            const spinbit:string = rawPacket["quic.spin_bit"];
            const spinbitBool: boolean = spinbit === "1";

            if (trace.spinbit !== spinbitBool) {
                trace.spinbit = spinbitBool;
                this.addEvent(trace, [
                    "" + trace.currentTime,
                    EventCategory.connectivity,
                    ConnectivityEventType.spin_bit_updated,
                    {
                        state: spinbitBool,
                    } as IEventSpinBitUpdated,
                ]);
            }
        }

        protected checkVersionUpdate( trace:TraceWrapper, header:qlog.IPacketHeader ) {
            if ( header.version !== "" && header.version !== undefined && trace.currentVersion !== header.version ) {
                this.addTrailingEvent(trace, [
                    "" + trace.currentTime,
                    EventCategory.transport,
                    TransportEventType.parameters_set,
                    {
                        version: header.version
                    } as qlog.IEventTransportParametersSet
                ]);

                trace.currentVersion = header.version!;
            }
        }

        protected checkCIDUpdate( trace:TraceWrapper, header:qlog.IPacketHeader ){
            
            if( header.dcid !== trace.currentServerCID && header.dcid !== trace.currentClientCID ) {
                // something changed in this header
                // we don't know which direction it is at this point, so need to check in both lists
                // lists do not need to contain the original CIDs because they are set the first time they're used 

                // we view from the client prespective, so server CID changes are destination, while client CID changes are source

                if ( this.debugging ) {
                    console.log("Something changed in the CID, checking : new CID ", header.dcid, ", current towards server: ", trace.currentServerCID, " current towards client: ", trace.currentClientCID );
                }

                // server issued this CID, so the client can use it to contact the server
                if ( trace.serverIssuedCIDs.indexOf(header.dcid!) ) { // if undefined, it's just not initialized yet: skip

                    this.addEvent(trace, [ // Log the change of cid
                        "" + trace.currentTime,
                        qlog.EventCategory.connectivity,
                        qlog.ConnectivityEventType.connection_id_updated,
                        {
                            dst_old: trace.currentServerCID,
                            dst_new: header.dcid,
                        } as qlog.IEventConnectionIDUpdated,
                    ]);

                    trace.currentServerCID = header.dcid; 
                }

                else if ( trace.clientIssuedCIDs.indexOf(header.dcid!) ) {

                    this.addEvent(trace, [ // Log the change of cid
                        "" + trace.currentTime,
                        qlog.EventCategory.connectivity,
                        qlog.ConnectivityEventType.connection_id_updated,
                        {
                            src_old: trace.currentClientCID,
                            src_new: header.dcid,
                        } as qlog.IEventConnectionIDUpdated,
                    ]);

                    trace.currentClientCID = header.dcid;
                }
                else {
                    this.exit("ParserPCAP:checkCIDUpdate: CID changed, but not to a value chosen by either client or server... shouldn't happen!", header, trace );
                }
            }
        }

        protected updateCIDsFromFrames( trace:TraceWrapper, frameContainingPacketHeader:qlog.IPacketHeader, frames:Array<qlog.QuicFrame> ) {
            
            const odcid = this.CIDToODCIDMap.get(frameContainingPacketHeader.dcid!);
            if ( !odcid ) {
                this.exit("updateCIDsFromFrames: header dcid didn't have a mapping itself!", frameContainingPacketHeader, this.CIDToODCIDMap );
            }

            const clientIssued = this.sentByClient( trace, frameContainingPacketHeader );

            for ( const frame of frames ) {
                if ( frame.frame_type === qlog.QUICFrameTypeName.new_connection_id ) {
                    this.CIDToODCIDMap.set( frame.connection_id, odcid! );

                    if ( clientIssued ) {
                        trace.clientIssuedCIDs.push( frame.connection_id );
                    }
                    else {
                        trace.serverIssuedCIDs.push( frame.connection_id );
                    }
                }
            }
        }

        protected getPacketType( rawQuicPacket:any ): qlog.PacketType {

            /* Example long packet:
            "quic.packet_length": "1252",
            "quic.header_form": "1",
            "quic.fixed_bit": "1",
            "quic.long.packet_type": "0",
            "quic.long.reserved": "0",
            "quic.packet_number_length": "0",
            "quic.version": "0xff00001d",
            "quic.dcil": "18",
            "quic.dcid": "f3:6e:07:bf:0b:70:88:ef:28:c7:1d:48:8a:ca:af:f3:9f:fc",
            "quic.scil": "17",
            "quic.scid": "43:94:4e:da:18:be:b7:e5:48:b3:8d:37:5b:f3:c2:a3:bc",
            "quic.token_length": "0",
            "quic.length": "1207",
            "quic.packet_number": "0",
            */

            /* example short packet:
            "quic.packet_length": "39",
            "quic.short": {
                "quic.header_form": "0",
                "quic.fixed_bit": "1",
                "quic.spin_bit": "0",
                "quic.dcid": "43:94:4e:da:18:be:b7:e5:48:b3:8d:37:5b:f3:c2:a3:bc"
            },
            */

            if ( rawQuicPacket["quic.header_form"] === "1" || rawQuicPacket["quic.long"] ){ // LONG header
                if ( rawQuicPacket["quic.long"] )
                    rawQuicPacket = rawQuicPacket["quic.long"];

                // if quic.version is 0, it's a version negotiation packet
                // otherwise, the packet type is in "quic.long.packet_type"
                const isVersionNegotiation: boolean = rawQuicPacket["quic.version"] !== undefined ? parseInt(rawQuicPacket["quic.version"], 16) === 0x00 : false;
                if ( isVersionNegotiation ) {
                    return qlog.PacketType.version_negotiation;
                }
                else {
                    const rawPacketType = parseInt( rawQuicPacket["quic.long.packet_type"], 16 );

                    if (rawPacketType === 0x00)
                        return qlog.PacketType.initial;
                    else if (rawPacketType === 0x01)
                        return qlog.PacketType.zerortt;
                    else if (rawPacketType === 0x02)
                        return qlog.PacketType.handshake;
                    else if (rawPacketType === 0x03)
                        return qlog.PacketType.retry;
                }
            }
            else if ( rawQuicPacket["quic.short"] ) {
                return qlog.PacketType.onertt;
            }
            else {
                return qlog.PacketType.unknown;
            }

            return qlog.PacketType.unknown;
        }

        protected convertPacketHeader( rawQuicPacket:any ): { packetType:qlog.PacketType, header: qlog.IPacketHeader | undefined } {
            let header = {} as qlog.IPacketHeader;

            let packetType:qlog.PacketType = this.getPacketType( rawQuicPacket );

            if ( packetType === qlog.PacketType.unknown ) {
                // some options may pass (e.g., padding/garbage in the rest of the UDP)
                if ( Object.keys(rawQuicPacket).length === 2 && 
                     rawQuicPacket["quic.packet_length"] && rawQuicPacket["quic.remaining_payload"] ) {
                    // garbage, ignore
                    if ( this.debugging ) {
                        console.log("convertPacketHeader: Found garbage packet, ignoring", rawQuicPacket);
                    }
                    return { packetType: packetType, header: undefined };
                }
                else {
                    this.exit("convertPacketHeader: unknown QUIC packet type found! ", rawQuicPacket );
                }
            }

            // the header doesn't always directly contain the packets... sometimes we have to go 1 level deeper (quic.short)
            // rawHeader is the header entrypoint, so tsharkQuicPacket can stay the packet entry point (needed for e.g., packet_length)
            let rawHeader = rawQuicPacket;

            if (  packetType !== qlog.PacketType.onertt ) // LONG header
            {
                // at the time of writing, there are no quic.long entries in tshark's output yet
                // however, they switched to using quic.short below, so we're trying some defensive programming here...
                if ( rawHeader["quic.long"] ){
                    rawHeader = rawHeader["quic.long"];
                }

                
                header.version = rawHeader["quic.version"];
                header.scid = this.getSourceConnectionID( rawHeader );
                header.dcid = this.getDestinationConnectionID( rawHeader );

                header.scil = "" + parseInt( rawHeader["quic.scil"], 10 );
                header.dcil = "" + parseInt( rawHeader["quic.dcil"], 10 );

                if ( packetType === qlog.PacketType.version_negotiation ) {
                    // supported versions are not part of the header in qlog, so not extracted here
                }
                else if ( packetType === qlog.PacketType.retry ) {
                    // TODO: rework when these fields are added to qlog proper
                    (header as any).token = rawHeader["quic.retry_token"];
                    (header as any).integrity_tag = ("" + rawHeader["quic.retry_integrity_tag"]).replace(/:/g, '');
                    if ( rawHeader["quic.retry_token"] ) {
                        (header as any).token_length = rawHeader["quic.retry_token"].replace(/:/g, '').length / 2; // TODO: verify how wireshark encodes this. We assume it's a : delimited hex field now
                    }
                }
                else { // initial, handshake, 0-RTT
                    header.packet_number = "" + rawHeader['quic.packet_number'];
                    header.packet_size = parseInt( rawQuicPacket["quic.packet_length"] ); // note: not part of the header in wireshark, but of the total quic packet

                    // for packets that cannot be decrypted, these fields are sometimes not present, so skip them in those cases
                    if ( rawHeader["quic.payload"] ) {
                        header.payload_length = rawHeader['quic.payload'].replace(/:/g, '').length / 2;
                    }
                    else {
                        header.payload_length = 0;
                    }

                    if ( packetType === qlog.PacketType.initial ) {
                        // TODO: rework when these fields are added to qlog proper
                        (header as any).token = rawHeader["quic.token"];
                        (header as any).token_length = parseInt( rawHeader["quic.token_length"] );
                    }
                }
            }
            else { // short header, 1rtt packet

                if ( rawHeader["quic.short"] ) {
                    rawHeader = rawHeader["quic.short"];
                }

                header.scid = undefined; // short headers don't carry this field, make sure it's not set
                header.dcid = this.getDestinationConnectionID( rawHeader );

                header.packet_number = "" + rawHeader['quic.packet_number'];
                header.packet_size = parseInt( rawQuicPacket["quic.packet_length"] ); // note: not part of the header in wireshark, but of the total quic packet

                // for packets that cannot be decrypted, these fields are sometimes not present, so skip them in those cases
                if ( rawHeader["quic.protected_payload"] ) {
                    header.payload_length = rawHeader['quic.protected_payload'].replace(/:/g, '').length / 2;
                }
                else {
                    header.payload_length = 0;
                }
            }

            return { packetType: packetType, header: header };
        }


        protected extractFrames(trace:TraceWrapper, rawPacket:any):Array<qlog.QuicFrame> {

            let output = [];

            let rawFrames:Array<qlog.QuicFrame> = [];

            if ( !rawPacket["quic.frame"] ) {
                return rawFrames;
            }

            if( Array.isArray(rawPacket["quic.frame"]) ){
                rawFrames = rawPacket["quic.frame"];
            }
            else {
                rawFrames = [ rawPacket["quic.frame"] ];
            }

            for (const rawFrame of rawFrames) {
                output.push( this.extractQlogFrame(trace, rawFrame));
            }

            return output;
        }


        private static extractALPNs(tsharkTLSHandshake: any): string[] {
            let alpnKey = undefined;
            for (const key of Object.keys(tsharkTLSHandshake)) {
                if (key.indexOf("layer_protocol_negotiation") >= 0) { // don't just check for protocol_negotation: NPN is next_protocol_negotiation...
                    alpnKey = key;
                    break;
                }
            }

            if (alpnKey !== undefined) {
                const alpnList = tsharkTLSHandshake[alpnKey]["tls.handshake.extensions_alpn_list"];
                if (Array.isArray(alpnList)) {
                    return alpnList.map((entry) => {
                        return entry["tls.handshake.extensions_alpn_str"];
                    });
                }
                else if (alpnList) {
                    return [alpnList["tls.handshake.extensions_alpn_str"]];
                }
            }
            
            return [];
        }

        public static findALPNs(tsharkCryptoFrame: any): string[] {
            if (tsharkCryptoFrame["tls.handshake"] === undefined) {
                return [];
            } else if (typeof tsharkCryptoFrame["tls.handshake"] === "string") {
                return [];
            } else if (Array.isArray(tsharkCryptoFrame["tls.handshake"])) {
                let alpns: string[] = [];
                for (const handshakeFrame of tsharkCryptoFrame["tls.handshake"]) {
                    alpns = alpns.concat(this.extractALPNs(handshakeFrame));
                }
                return alpns;
            } else {
                return this.extractALPNs(tsharkCryptoFrame["tls.handshake"]);
            }
        }

        // TODO move to util file
        protected extractQlogFrame( trace:TraceWrapper, rawFrame: any ): QuicFrame {
            const frameType = PCAPUtil.getFrameTypeName(parseInt(rawFrame["quic.frame_type"]));

            switch (frameType) {
                case QUICFrameTypeName.padding:
                    return ParserPCAP.convertPaddingFrame(rawFrame);
                case QUICFrameTypeName.ping:
                    return ParserPCAP.convertPingFrame(rawFrame);
                case QUICFrameTypeName.ack:
                    return ParserPCAP.convertAckFrame(rawFrame);
                case QUICFrameTypeName.reset_stream:
                    return ParserPCAP.convertResetStreamFrame(rawFrame);
                case QUICFrameTypeName.stop_sending:
                    return ParserPCAP.convertStopSendingFrame(rawFrame);
                case QUICFrameTypeName.crypto:
                    const alpns: string[] = ParserPCAP.findALPNs(rawFrame);

                    // ALPN can only be selected by server
                    if (alpns.length === 1 && trace.selectedALPN === undefined) {
                        this.addTrailingEvent(trace, [
                            "" + trace.currentTime,
                            EventCategory.transport,
                            TransportEventType.parameters_set,
                            {
                                owner: "remote",
                                alpn: alpns[0],
                            } as IEventTransportParametersSet,
                        ]);
                        trace.selectedALPN = alpns[0];
                    }
                    return ParserPCAP.convertCryptoFrame(rawFrame);
                case QUICFrameTypeName.new_token:
                    return ParserPCAP.convertNewTokenFrame(rawFrame);
                case QUICFrameTypeName.stream:
                    return ParserPCAP.convertStreamFrame(rawFrame);
                case QUICFrameTypeName.max_data:
                    return ParserPCAP.convertMaxDataFrame(rawFrame);
                case QUICFrameTypeName.max_stream_data:
                    return ParserPCAP.convertMaxStreamDataFrame(rawFrame);
                case QUICFrameTypeName.max_streams:
                    return ParserPCAP.convertMaxStreamsFrame(rawFrame);
                case QUICFrameTypeName.stream_data_blocked:
                    return ParserPCAP.convertStreamDataBlockedFrame(rawFrame);
                case QUICFrameTypeName.streams_blocked:
                    return ParserPCAP.convertStreamsBlockedFrame(rawFrame);
                case QUICFrameTypeName.new_connection_id:
                    return ParserPCAP.convertNewConnectionIDFrame(rawFrame);
                case QUICFrameTypeName.retire_connection_id:
                    return ParserPCAP.convertRetireConnectionIDFrame(rawFrame);
                case QUICFrameTypeName.path_challenge:
                    return ParserPCAP.convertPathChallengeFrame(rawFrame);
                case QUICFrameTypeName.path_response:
                    return ParserPCAP.convertPathResponseFrame(rawFrame);
                case QUICFrameTypeName.connection_close:
                    // Event should only be added after PacketReceived/PacketSent event
                    this.addTrailingEvent(trace, [
                        trace.currentTime,
                        EventCategory.connectivity,
                        ConnectivityEventType.connection_state_updated,
                        {
                            new: ConnectionState.closed
                        } as IEventConnectionStateUpdated,
                    ]);
                    return ParserPCAP.convertConnectionCloseFrame(rawFrame);
                default:
                    if ( parseInt(rawFrame["quic.frame_type"]) === 30 ) { // TODO: handle properly once we update the qlog library
                        return ParserPCAP.convertHandshakeDoneFrame( rawFrame );
                    }
                    else {
                        if( this.debugging ) {
                            console.log("Unknown frame type found ", rawFrame["quic.frame_type"], rawFrame );
                        }
                        let frame: IUnknownFrame = {
                            frame_type: QUICFrameTypeName.unknown_frame_type,
                            raw_frame_type: rawFrame["quic.frame_type"],
                        }
                        if (this.logUnknownFramesFields) {
                            (frame as any).raw_frame_content = rawFrame;
                        }
                        return frame;
                    }
            }
        }

        public static convertPaddingFrame(tsharkPaddingFrame: any): IPaddingFrame {
            return {
                frame_type: QUICFrameTypeName.padding,
            };
        }

        public static convertPingFrame(tsharkPingFrame: any): IPingFrame {
            return {
                frame_type: QUICFrameTypeName.ping,
            };
        }

        public static convertAckFrame(tsharkAckFrame: any): IAckFrame {
            const isEcn: boolean = tsharkAckFrame["quic.frame_type"] === "3" ? true : false;
            const ackRangeCount: number = parseInt(tsharkAckFrame['quic.ack.ack_range_count']);
            const ackedRanges: [string, string][] = [];
            let topAck: number = parseInt(tsharkAckFrame['quic.ack.largest_acknowledged']);
            let bottomAck = topAck - parseInt(tsharkAckFrame['quic.ack.first_ack_range']);

            ackedRanges.unshift([bottomAck.toString(), topAck.toString()]);
            if (ackRangeCount === 1) { // 1 gap
                let gap: number = parseInt(tsharkAckFrame['quic.ack.gap']) + 2;
                topAck = bottomAck - gap;
                bottomAck = topAck - parseInt(tsharkAckFrame['quic.ack.ack_range']);
                ackedRanges.unshift([bottomAck.toString(), topAck.toString()]);
            } else if (ackRangeCount > 1) { // multiple gaps
                let gap: number;
                for (let i = 0; i < ackRangeCount; ++i) {
                    gap = parseInt(tsharkAckFrame['quic.ack.gap'][i]) + 2;
                    topAck = bottomAck - gap;
                    bottomAck = topAck - parseInt(tsharkAckFrame['quic.ack.ack_range'][i]);
                    ackedRanges.unshift([bottomAck.toString(), topAck.toString()]);
                }
            }

            return {
                frame_type: QUICFrameTypeName.ack,
                ack_delay: tsharkAckFrame["quic.ack.ack_delay"],
                acked_ranges: ackedRanges,
                ce: isEcn ? tsharkAckFrame["quic.ack.ecn_ce_count"] : undefined,
                ect0: isEcn ? tsharkAckFrame["quic.ack.ect0_count"] : undefined,
                ect1: isEcn ? tsharkAckFrame["quic.ack.ect1_count"] : undefined,
            };
        }

        public static convertResetStreamFrame(tsharkResetStreamFrame: any): IResetStreamFrame {
            return {
                frame_type: QUICFrameTypeName.reset_stream,

                stream_id: tsharkResetStreamFrame["quic.rsts.stream_id"],
                error_code: tsharkResetStreamFrame["quic.rsts.application_error_code"],
                final_size: tsharkResetStreamFrame["quic.rsts.final_size"],
            }
        }

        public static convertStopSendingFrame(tsharkStopSendingFrame: any): IStopSendingFrame {
            return {
                frame_type: QUICFrameTypeName.stop_sending,

                stream_id: tsharkStopSendingFrame["quic.ss.stream_id"],
                error_code: tsharkStopSendingFrame["quic.ss.application_error_code"],
            };
        }

        public static convertCryptoFrame(tsharkCryptoFrame: any): ICryptoFrame {
            return {
                frame_type: QUICFrameTypeName.crypto,

                offset: tsharkCryptoFrame["quic.crypto.offset"],
                length: tsharkCryptoFrame["quic.crypto.length"],
            };
        }

        public static convertNewTokenFrame(tsharkNewTokenFrame: any): INewTokenFrame {
            return {
                frame_type: QUICFrameTypeName.new_token,

                length: tsharkNewTokenFrame["quic.nt.length"],
                token: tsharkNewTokenFrame["quic.nt.token"].replace(/:/g, ''),
            };
        }


        public static convertStreamFrame(tsharkStreamFrame: any): IStreamFrame {
            return {
                frame_type: QUICFrameTypeName.stream,

                stream_id: tsharkStreamFrame["quic.stream.stream_id"],

                offset: tsharkStreamFrame['quic.frame_type_tree']['quic.stream.off'] === "1" ? tsharkStreamFrame["quic.stream.offset"] : "0",
                length: tsharkStreamFrame["quic.stream.length"],

                fin: tsharkStreamFrame["quic.frame_type_tree"]["quic.stream.fin"] === "1",
                // raw: logRawPayloads ? tsharkStreamFrame["quic.stream_data"].replace(/:/g, '') : undefined,
            };
        }

        public static convertMaxDataFrame(tsharkMaxDataFrame: any): IMaxDataFrame {
            return {
                frame_type: QUICFrameTypeName.max_data,

                maximum: tsharkMaxDataFrame["quic.md.maximum_data"],
            }
        }

        public static convertMaxStreamDataFrame(tsharkMaxStreamDataFrame: any): IMaxStreamDataFrame {
            return {
                frame_type: QUICFrameTypeName.max_stream_data,

                stream_id: tsharkMaxStreamDataFrame["quic.msd.stream_id"],
                maximum: tsharkMaxStreamDataFrame["quic.msd.maximum_stream_data"],
            };
        }

        public static convertMaxStreamsFrame(tsharkMaxStreamsFrame: any): IMaxStreamsFrame {
            return {
                frame_type: QUICFrameTypeName.max_streams,

                stream_type: tsharkMaxStreamsFrame["quic.frame_type"] === "18" ? "bidirectional" : "unidirectional",
                maximum: tsharkMaxStreamsFrame["quic.ms.max_streams"],
            };
        }

        public static convertDataBlockedFrame(tsharkDataBlockedFrame: any): IDataBlockedFrame {
            return {
                frame_type: QUICFrameTypeName.data_blocked,

                limit: tsharkDataBlockedFrame["quic.sb.stream_data_limit"],
            };
        }

        public static convertStreamDataBlockedFrame(tsharkStreamDataBlockedFrame: any): IStreamDataBlockedFrame {
            return {
                frame_type: QUICFrameTypeName.stream_data_blocked,

                stream_id: tsharkStreamDataBlockedFrame["quic.sdb.stream_id"],
                limit: tsharkStreamDataBlockedFrame["quic.sb.stream_data_limit"],
            }
        }

        public static convertStreamsBlockedFrame(tsharkStreamsBlockedFrame: any): IStreamsBlockedFrame {
            return  {
                frame_type: QUICFrameTypeName.streams_blocked,

                stream_type: tsharkStreamsBlockedFrame["quic.frame_type"] === "22" ? "bidirectional" : "unidirectional",
                limit: tsharkStreamsBlockedFrame["quic.sib.stream_limit"],
            };
        }

        public static convertNewConnectionIDFrame(tsharkNewConnectionIDFrame: any): INewConnectionIDFrame {
            return {
                frame_type: QUICFrameTypeName.new_connection_id,

                retire_prior_to: tsharkNewConnectionIDFrame["quic.nci.retire_prior_to"],
                sequence_number: tsharkNewConnectionIDFrame["quic.nci.sequence"],
                connection_id: tsharkNewConnectionIDFrame["quic.nci.connection_id"].replace(/:/g, ''),
                length: tsharkNewConnectionIDFrame["quic.nci.connection_id.length"],
                reset_token: tsharkNewConnectionIDFrame["quic.stateless_reset_token"].replace(/:/g, ''),
            };
        }

        public static convertRetireConnectionIDFrame(tsharkRetireConnectionIDFrame: any): IRetireConnectionIDFrame {
            return {
                frame_type: QUICFrameTypeName.retire_connection_id,

                sequence_number: tsharkRetireConnectionIDFrame["quic.rci.sequence"],
            };
        }

        public static convertPathChallengeFrame(tsharkPathChallengeFrame: any): IPathChallengeFrame {
            return {
                frame_type: QUICFrameTypeName.path_challenge,

                data: tsharkPathChallengeFrame["quic.path_challenge.data"].replace(/:/g, ''),
            };
        }

        public static convertPathResponseFrame(tsharkPathResponseFrame: any): IPathResponseFrame {
            return {
                frame_type: QUICFrameTypeName.path_response,
            };
        }

        public static convertConnectionCloseFrame(tsharkConnectionCloseFrame: any): IConnectionCloseFrame {
            const inApplicationLayer: boolean = tsharkConnectionCloseFrame["quic.frame_type"] === "29";
            return {
                frame_type: QUICFrameTypeName.connection_close,

                error_space: inApplicationLayer ? qlog.ErrorSpace.transport_error : qlog.ErrorSpace.transport_error,
                error_code: inApplicationLayer ? this.applicationErrorCodeToEnum(tsharkConnectionCloseFrame["quic.cc.error_code.app"]) : this.transportErrorCodeToEnum(tsharkConnectionCloseFrame["quic.cc.error_code"]),
                raw_error_code: inApplicationLayer ? tsharkConnectionCloseFrame["quic.cc.error_code.app"] : tsharkConnectionCloseFrame["quic.cc.error_code"],
                reason: tsharkConnectionCloseFrame["quic.cc.reason_phrase"],

                trigger_frame_type: tsharkConnectionCloseFrame["quic.cc.frame_type"],
            };
        }

        public static convertHandshakeDoneFrame( tsharkHandshakeDoneFrame: any ): any {
            return {
                frame_type: "handshake_done" // FIXME: add properly when we update the qlog library
            };
        }

        public static transportErrorCodeToEnum(errorCode: string): TransportError | string {
            const errorCodeNumber: number = parseInt(errorCode);
            if (errorCodeNumber === 0x00) {
                return TransportError.no_error;
            } else if (errorCodeNumber === 0x01) {
                return TransportError.internal_error;
            } else if (errorCodeNumber === 0x02) {
                return TransportError.server_busy;
            } else if (errorCodeNumber === 0x03) {
                return TransportError.flow_control_error;
            } else if (errorCodeNumber === 0x04) {
                return TransportError.stream_limit_error;
            } else if (errorCodeNumber === 0x05) {
                return TransportError.stream_state_error;
            } else if (errorCodeNumber === 0x06) {
                return TransportError.final_size_error;
            } else if (errorCodeNumber === 0x07) {
                return TransportError.frame_encoding_error;
            } else if (errorCodeNumber === 0x08) {
                return TransportError.transport_parameter_error;
            } else if (errorCodeNumber === 0x0a) {
                return TransportError.protocol_violation;
            } else if (errorCodeNumber === 0x0d) {
                return TransportError.crypto_buffer_exceeded;
            } else if (errorCodeNumber >= 0x100 && errorCodeNumber <= 0x1ff) {
                return CryptoError.prefix + "" + errorCodeNumber;
            } else {
                return TransportError.unknown;
            }
        }

        public static applicationErrorCodeToEnum(errorCode: string): ApplicationError {
            const errorCodeNumber: number = parseInt(errorCode);
            // FIXME Currently assumes HTTP as only application layer protocol
            if (errorCodeNumber === 0x0100) {
                return ApplicationError.http_no_error;
            } else if (errorCodeNumber === 0x0101) {
                return ApplicationError.http_general_protocol_error;
            } else if (errorCodeNumber === 0x0102) {
                return ApplicationError.http_internal_error;
            } else if (errorCodeNumber === 0x0103) {
                return ApplicationError.http_stream_creation_error;
            } else if (errorCodeNumber === 0x0104) {
                return ApplicationError.http_closed_critical_stream;
            } else if (errorCodeNumber === 0x0105) {
                return ApplicationError.http_frame_unexpected;
            } else if (errorCodeNumber === 0x0106) {
                return ApplicationError.http_frame_error;
            } else if (errorCodeNumber === 0x0107) {
                return ApplicationError.http_excessive_load;
            } else if (errorCodeNumber === 0x0108) {
                return ApplicationError.http_id_error;
            } else if (errorCodeNumber === 0x0109) {
                return ApplicationError.http_settings_error;
            } else if (errorCodeNumber === 0x010a) {
                return ApplicationError.http_missing_settings;
            } else if (errorCodeNumber === 0x010b) {
                return ApplicationError.http_request_rejected;
            } else if (errorCodeNumber === 0x010c) {
                return ApplicationError.http_request_cancelled;
            } else if (errorCodeNumber === 0x010d) {
                return ApplicationError.http_request_incomplete;
            } else if (errorCodeNumber === 0x010e) {
                return ApplicationError.http_early_response;
            } else if (errorCodeNumber === 0x010f) {
                return ApplicationError.http_connect_error;
            } else if (errorCodeNumber === 0x0110) {
                return ApplicationError.http_version_fallback;
            } else {
                return ApplicationError.unknown;
            }
        }

        public getQUICVersion(packet:any): string {
            if (packet['quic.header_form'] === '1') {
                return packet['quic.version'];
            }
            else if ( packet["quic.long"] ){
                return packet["quic.long"]['quic.version'];
            }
            else {
                return 'None';
            }
        }

        protected getSourceConnectionID( header:any ): string {
            if ( header['quic.scid'] )
                return header['quic.scid'].replace(/:/g, '');
            else 
                return ParserPCAP.DEFAULT_SCID;
        }

        protected getDestinationConnectionID(header:any): string {
            if ( header['quic.dcid'] )
                return header['quic.dcid'].replace(/:/g, '');
            else 
                return ParserPCAP.DEFAULT_DCID;
        }

        public getTime(frame:any): number {
            return parseFloat(frame['frame.time_epoch']);
        }

        public getConnectionInfo(firstEntry:any, firstPacketHeader:qlog.IPacketHeader) {
            let layer_ip = firstEntry['_source']['layers']['ip'];
            let layer_udp = firstEntry['_source']['layers']['udp'];

            if ( !layer_udp ) {
                console.log("Trying to find UDP stuff, but doesn't exist... wth: ", firstEntry);
            }

            if(!layer_ip) {
                layer_ip = firstEntry['_source']['layers']['ipv6'];
                return {
                    ip_version: layer_ip['ipv6.version'],
                    src_ip: layer_ip['ipv6.src'],
                    dst_ip: layer_ip['ipv6.dst'],
                    protocol: "QUIC",
                    src_port: layer_udp['udp.srcport'],
                    dst_port: layer_udp['udp.dstport'],
                    quic_version: firstPacketHeader.version,
                    src_cid: firstPacketHeader.scid,
                    dst_cid: firstPacketHeader.dcid
                }
            }

            return {
                ip_version: layer_ip['ip.version'],
                src_ip: layer_ip['ip.src'],
                dst_ip: layer_ip['ip.dst'],
                protocol: "QUIC",
                src_port: layer_udp['udp.srcport'],
                dst_port: layer_udp['udp.dstport'],
                quic_version: firstPacketHeader.version,
                src_cid: firstPacketHeader.scid,
                dst_cid: firstPacketHeader.dcid
            }
        }
}
