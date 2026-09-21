import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
record = json.loads((root / "campaign.json").read_text())
for name, digest in sorted(record["prompt_sha256"].items()):
    actual = hashlib.sha256((root / "prompts" / name).read_bytes()).hexdigest()
    print("OK " if actual == digest else "BAD", name, digest)
for key in ("window", "target", "model", "effort", "claude_version", "parity",
            "session_mode", "consolidate_every", "run_order", "pristine_sha256",
            "toolchain_sha256"):
    print(key, "=", record[key])
print("vcs =", record["git"])
arm_b = (root / "prompts" / "arm-B.md").read_text()
print("arm-B code anchor:", '"evidence_class": "code"' in arm_b)
print("arm-B adr anchor:", '"evidence_class": "adr"' in arm_b)
