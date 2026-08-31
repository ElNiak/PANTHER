"""Allow ``python -m panther.plugins.services.testers.a_rfc.pipeline``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
