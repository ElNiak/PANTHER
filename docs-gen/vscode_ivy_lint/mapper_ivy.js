// path/filename: mapper_ivy.js
// Custom mapper for `.ivy` files for the CodeMap VSCode extension

"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const fs = require("fs");

// Define the mapper class with necessary static methods
class mapper {
    // Method to read all lines from the file
    static read_all_lines(file) {
        let text = fs.readFileSync(file, 'utf8');
        return text.split(/\r?\n/g);
    }

    // Method to generate the code map based on the .ivy file syntax
    static generate(file) {
        let members = [];
        try {
            let line_num = 0;
            mapper.read_all_lines(file).forEach(line => {
                line_num++;
                line = line.trimStart();

                // Add custom mapping rules for .ivy syntax
                if (line.startsWith("# "))
                    members.push(`${line.substr(4)}|${line_num}|comment`);
                else if (line.startsWith("function "))
                    members.push(`${line.substr(4)}|${line_num}|function`);
                else if (line.startsWith("class "))
                    members.push(`${line.substr(6)}|${line_num}|class`);
                else if (line.startsWith("type "))
                    members.push(`${line.substr(5)}|${line_num}|type`);
                else if (line.startsWith("relation "))
                    members.push(`${line.substr(9)}|${line_num}|relation`);
                else if (line.startsWith("axiom "))
                    members.push(`${line.substr(6)}|${line_num}|axiom`);
                else if (line.startsWith("conjecture "))
                    members.push(`${line.substr(10)}|${line_num}|conjecture`);
                else if (line.startsWith("schema "))
                    members.push(`${line.substr(7)}|${line_num}|schema`);
                else if (line.startsWith("instantiate "))
                    members.push(`${line.substr(11)}|${line_num}|instantiate`);
                else if (line.startsWith("action "))
                    members.push(`${line.substr(7)}|${line_num}|action`);
                else if (line.startsWith("method "))
                    members.push(`${line.substr(7)}|${line_num}|method`);
                else if (line.startsWith("field "))
                    members.push(`${line.substr(6)}|${line_num}|field`);
                else if (line.startsWith("state "))
                    members.push(`${line.substr(6)}|${line_num}|state`);
                else if (line.startsWith("assume "))
                    members.push(`${line.substr(7)}|${line_num}|assume`);
                else if (line.startsWith("assert "))
                    members.push(`${line.substr(7)}|${line_num}|assert`);
                else if (line.startsWith("set "))
                    members.push(`${line.substr(4)}|${line_num}|set`);
                else if (line.startsWith("null "))
                    members.push(`${line.substr(5)}|${line_num}|null`);
                else if (line.startsWith("from "))
                    members.push(`${line.substr(5)}|${line_num}|from`);
                else if (line.startsWith("update "))
                    members.push(`${line.substr(7)}|${line_num}|update`);
                else if (line.startsWith("params "))
                    members.push(`${line.substr(7)}|${line_num}|params`);
                else if (line.startsWith("in "))
                    members.push(`${line.substr(3)}|${line_num}|in`);
                else if (line.startsWith("match "))
                    members.push(`${line.substr(6)}|${line_num}|match`);
                else if (line.startsWith("ensures "))
                    members.push(`${line.substr(8)}|${line_num}|ensures`);
                else if (line.startsWith("requires "))
                    members.push(`${line.substr(9)}|${line_num}|requires`);
                else if (line.startsWith("modifies "))
                    members.push(`${line.substr(9)}|${line_num}|modifies`);
                else if (line.startsWith("true "))
                    members.push(`${line.substr(5)}|${line_num}|true`);
                else if (line.startsWith("false "))
                    members.push(`${line.substr(6)}|${line_num}|false`);
                else if (line.startsWith("fresh "))
                    members.push(`${line.substr(6)}|${line_num}|fresh`);
                else if (line.startsWith("module "))
                    members.push(`${line.substr(7)}|${line_num}|module`);
                else if (line.startsWith("template "))
                    members.push(`${line.substr(9)}|${line_num}|template`);
                else if (line.startsWith("object "))
                    members.push(`${line.substr(7)}|${line_num}|object`);
                else if (line.startsWith("if "))
                    members.push(`${line.substr(3)}|${line_num}|if`);
                else if (line.startsWith("else "))
                    members.push(`${line.substr(5)}|${line_num}|else`);
                else if (line.startsWith("let "))
                    members.push(`${line.substr(4)}|${line_num}|let`);
                else if (line.startsWith("call "))
                    members.push(`${line.substr(5)}|${line_num}|call`);
                else if (line.startsWith("entry "))
                    members.push(`${line.substr(6)}|${line_num}|entry`);
                else if (line.startsWith("macro "))
                    members.push(`${line.substr(6)}|${line_num}|macro`);
                else if (line.startsWith("interpret "))
                    members.push(`${line.substr(10)}|${line_num}|interpret`);
                else if (line.startsWith("forall "))
                    members.push(`${line.substr(7)}|${line_num}|forall`);
                else if (line.startsWith("exists "))
                    members.push(`${line.substr(7)}|${line_num}|exists`);
                else if (line.startsWith("returns "))
                    members.push(`${line.substr(8)}|${line_num}|returns`);
                else if (line.startsWith("mixin "))
                    members.push(`${line.substr(6)}|${line_num}|mixin`);
                else if (line.startsWith("before "))
                    members.push(`${line.substr(7)}|${line_num}|before`);
                else if (line.startsWith("after "))
                    members.push(`${line.substr(6)}|${line_num}|after`);
                else if (line.startsWith("isolate "))
                    members.push(`${line.substr(8)}|${line_num}|isolate`);
                else if (line.startsWith("with "))
                    members.push(`${line.substr(5)}|${line_num}|with`);
                else if (line.startsWith("export "))
                    members.push(`${line.substr(7)}|${line_num}|export`);
                else if (line.startsWith("delegate "))
                    members.push(`${line.substr(9)}|${line_num}|delegate`);
                else if (line.startsWith("import "))
                    members.push(`${line.substr(7)}|${line_num}|import`);
                else if (line.startsWith("using "))
                    members.push(`${line.substr(6)}|${line_num}|using`);
                else if (line.startsWith("include "))
                    members.push(`${line.substr(8)}|${line_num}|include`);
                else if (line.startsWith("progress "))
                    members.push(`${line.substr(9)}|${line_num}|progress`);
                else if (line.startsWith("rely "))
                    members.push(`${line.substr(5)}|${line_num}|rely`);
                else if (line.startsWith("mixord "))
                    members.push(`${line.substr(7)}|${line_num}|mixord`);
                else if (line.startsWith("extract "))
                    members.push(`${line.substr(8)}|${line_num}|extract`);
                else if (line.startsWith("process "))
                    members.push(`${line.substr(8)}|${line_num}|process`);
                else if (line.startsWith("destructor "))
                    members.push(`${line.substr(11)}|${line_num}|destructor`);
                else if (line.startsWith("maximizing "))
                    members.push(`${line.substr(11)}|${line_num}|maximizing`);
                else if (line.startsWith("minimizing "))
                    members.push(`${line.substr(11)}|${line_num}|minimizing`);
                else if (line.startsWith("private "))
                    members.push(`${line.substr(8)}|${line_num}|private`);
                else if (line.startsWith("implement "))
                    members.push(`${line.substr(10)}|${line_num}|implement`);
                else if (line.startsWith("property "))
                    members.push(`${line.substr(9)}|${line_num}|property`);
                else if (line.startsWith("while "))
                    members.push(`${line.substr(6)}|${line_num}|while`);
                else if (line.startsWith("invariant "))
                    members.push(`${line.substr(10)}|${line_num}|invariant`);
                else if (line.startsWith("struct "))
                    members.push(`${line.substr(7)}|${line_num}|struct`);
                else if (line.startsWith("definition "))
                    members.push(`${line.substr(11)}|${line_num}|definition`);
                else if (line.startsWith("ghost "))
                    members.push(`${line.substr(6)}|${line_num}|ghost`);
                else if (line.startsWith("alias "))
                    members.push(`${line.substr(6)}|${line_num}|alias`);
                else if (line.startsWith("trusted "))
                    members.push(`${line.substr(8)}|${line_num}|trusted`);
                else if (line.startsWith("this "))
                    members.push(`${line.substr(5)}|${line_num}|this`);
                else if (line.startsWith("var "))
                    members.push(`${line.substr(4)}|${line_num}|var`);
                else if (line.startsWith("attribute "))
                    members.push(`${line.substr(10)}|${line_num}|attribute`);
                else if (line.startsWith("variant "))
                    members.push(`${line.substr(8)}|${line_num}|variant`);
                else if (line.startsWith("of "))
                    members.push(`${line.substr(3)}|${line_num}|of`);
                else if (line.startsWith("scenario "))
                    members.push(`${line.substr(9)}|${line_num}|scenario`);
                else if (line.startsWith("proof "))
                    members.push(`${line.substr(6)}|${line_num}|proof`);
                else if (line.startsWith("named "))
                    members.push(`${line.substr(6)}|${line_num}|named`);
                else if (line.startsWith("temporal "))
                    members.push(`${line.substr(9)}|${line_num}|temporal`);
                else if (line.startsWith("globally "))
                    members.push(`${line.substr(9)}|${line_num}|globally`);
                else if (line.startsWith("eventually "))
                    members.push(`${line.substr(11)}|${line_num}|eventually`);
                else if (line.startsWith("decreases "))
                    members.push(`${line.substr(10)}|${line_num}|decreases`);
                else if (line.startsWith("specification "))
                    members.push(`${line.substr(14)}|${line_num}|specification`);
                else if (line.startsWith("implementation "))
                    members.push(`${line.substr(14)}|${line_num}|implementation`);
                else if (line.startsWith("global "))
                    members.push(`${line.substr(7)}|${line_num}|global`);
                else if (line.startsWith("common "))
                    members.push(`${line.substr(7)}|${line_num}|common`);
                else if (line.startsWith("ensure "))
                    members.push(`${line.substr(7)}|${line_num}|ensure`);
                else if (line.startsWith("require "))
                    members.push(`${line.substr(8)}|${line_num}|require`);
                else if (line.startsWith("around "))
                    members.push(`${line.substr(7)}|${line_num}|around`);
                else if (line.startsWith("parameter "))
                    members.push(`${line.substr(10)}|${line_num}|parameter`);
                else if (line.startsWith("apply "))
                    members.push(`${line.substr(6)}|${line_num}|apply`);
                else if (line.startsWith("theorem "))
                    members.push(`${line.substr(8)}|${line_num}|theorem`);
                else if (line.startsWith("showgoals "))
                    members.push(`${line.substr(10)}|${line_num}|showgoals`);
                else if (line.startsWith("defergoal "))
                    members.push(`${line.substr(10)}|${line_num}|defergoal`);
                else if (line.startsWith("spoil "))
                    members.push(`${line.substr(6)}|${line_num}|spoil`);
                else if (line.startsWith("explicit "))
                    members.push(`${line.substr(9)}|${line_num}|explicit`);
                else if (line.startsWith("thunk "))
                    members.push(`${line.substr(6)}|${line_num}|thunk`);
                else if (line.startsWith("isa "))
                    members.push(`${line.substr(4)}|${line_num}|isa`);
                else if (line.startsWith("autoinstance "))
                    members.push(`${line.substr(12)}|${line_num}|autoinstance`);
                else if (line.startsWith("constructor "))
                    members.push(`${line.substr(12)}|${line_num}|constructor`);
                else if (line.startsWith("finite "))
                    members.push(`${line.substr(7)}|${line_num}|finite`);
                else if (line.startsWith("tactic "))
                    members.push(`${line.substr(7)}|${line_num}|tactic`);
                else if (line.startsWith("unfold "))
                    members.push(`${line.substr(7)}|${line_num}|unfold`);
                else if (line.startsWith("forget "))
                    members.push(`${line.substr(7)}|${line_num}|forget`);
                else if (line.startsWith("debug "))
                    members.push(`${line.substr(6)}|${line_num}|debug`);
                else if (line.startsWith("for "))
                    members.push(`${line.substr(4)}|${line_num}|for`);
                else if (line.startsWith("subclass "))
                    members.push(`${line.substr(9)}|${line_num}|subclass`);
            });
        } catch (error) {
            console.error(`Error processing file ${file}: ${error}`);
        }
        return members;
    }
}

// Export the mapper class
exports.mapper = mapper;
