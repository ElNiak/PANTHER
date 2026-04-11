## Debugging Ivy/BGP Compilation & Verification

When debugging Ivy/BGP compilation or verification errors, always check MCP sidecar staging paths and include resolution before investigating code-level issues. Hardcoded Docker network addresses and stale process state are common root causes.

Before investigating any Ivy compilation or verification failure, follow this triage order:

1. Is the MCP sidecar running and healthy?
2. Are `staging_dir` paths correct?
3. Are include paths resolving to local files (not Docker addresses)?
4. Is there stale process state (leftover PIDs, zombie processes)?

Only after confirming infrastructure is healthy, investigate the code itself.

When an MCP server drops or returns errors, treat it as an infrastructure issue until proven otherwise. Do not attribute MCP failures to application-level bugs, hallucinations, or Claude-side errors without concrete evidence.

After running health checks or diagnostics, investigate ALL warnings -- they have historically revealed real bugs (sidecar early-capture bugs, stale PIDs, missing resolvers). Do not dismiss warnings as benign without investigation.
