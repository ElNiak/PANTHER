"""Re-run the build report's own make argv for one target and show its raw output."""

import json
import subprocess
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
target = sys.argv[2]
argv = [a for a in report["argv"] if a not in ("txt", "html", "lint", "idnits")] + [target]
argv = [a for a in argv if not a.startswith("TRACE_FILE=")]
result = subprocess.run(argv, capture_output=True, text=True)
print("exit:", result.returncode)
print("--- stdout (last 40 lines)")
print("\n".join(result.stdout.splitlines()[-40:]))
print("--- stderr (last 40 lines)")
print("\n".join(result.stderr.splitlines()[-40:]))
