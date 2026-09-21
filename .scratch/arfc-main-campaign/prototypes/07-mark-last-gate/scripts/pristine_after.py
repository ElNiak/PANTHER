import sys
from pathlib import Path

from ai_rfc.experiment.workspace import verify_digest

print("pristine digest problems after:", verify_digest(Path(sys.argv[1])) or "none")
