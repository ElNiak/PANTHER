# ai_rfc — reconstructed specifications

`ai_rfc` reconstructs an RFC-style specification from a software project's own
history and gates every claim against the evidence behind it. It is its own
project, consumed here as the submodule `panther/plugins/services/testers/ai_rfc`
and installed by `panther build dev`.

- `panther ai-rfc <verb>` forwards to the tool's own `ai-rfc <verb>` and
  returns its exit code unchanged (0 clean, 1 unusable input, 2 malformed
  invocation, 3 strict findings).
- `ai-rfc --help` lists every verb in workflow order.
- The tool's documentation, schema, promotion rule and design records live in
  its repository: <https://github.com/ElNiak/ai_rfc>.
