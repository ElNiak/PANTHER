const fs = require('fs');
const path = require('path');

const crypto = require("crypto");

// https://stackoverflow.com/questions/31645738/how-to-create-full-path-with-nodes-fs-mkdirsync
export function mkDirByPathSync(targetDir:string, {isRelativeToScript = false} = {}) {
  const sep = path.sep;
  const initDir = path.isAbsolute(targetDir) ? sep : '';
  const baseDir = isRelativeToScript ? __dirname : '.';

  targetDir.split(sep).reduce((parentDir, childDir) => {
    const curDir = path.resolve(baseDir, parentDir, childDir);
    try {
      if (!fs.existsSync(curDir)) {
        fs.mkdirSync(curDir);
      }
      //console.log(`Directory ${curDir} created!`);
    } catch (err) {
      if (err.code !== 'EEXIST' && err.code !== "EISDIR" &&
          !(err.code == 'EPERM' && curDir == "C:\\") ) {
        throw err;
      }

      //console.log(`Directory ${curDir} already exists!`);
    }

    return curDir;
  }, initDir);

}

export function createHash(contents:string){
    return crypto.createHash('sha1').update( contents ).digest('hex');
}


export function getFileExtension(target:string){

    let ext:string = path.extname(target); // gives extensions including the dot, e.g., .json 
    
    if( !ext || ext.length == 0 ){
        if( fileIsJSON(target) )
            ext = ".json";
        else if( fileIsPCAP(target) )
            ext = ".pcap";
        else if( fileIsSECRETS(target) )
            ext = ".keys";
        else if( fileIsQLOG(target) ){
            ext = ".qlog";
        }
    }

    return ext;
}

export function fileIsJSON(path:string){
    return path.indexOf(".json") >= 0;
}
export function fileIsPCAP(path:string){
    // either .pcap or simply pcap at the end (e.g., quic-tracker has a url in the form   quick-tracker.com/trace/xyz/pcap)
    return path.indexOf(".pcap") >= 0 || path.slice(-5) === "/pcap";
}
export function fileIsSECRETS(path:string){
    // either .keys/.secrets or simply secrets at the end (e.g., quic-tracker has a url in the form   quick-tracker.com/trace/xyz/secrets)
    return path.indexOf(".secrets") >= 0 || path.indexOf(".keys") >= 0 || path.slice(-8) === "/secrets";
}
export function fileIsQLOG(path:string){
    return path.indexOf(".qlog") >= 0;
}
