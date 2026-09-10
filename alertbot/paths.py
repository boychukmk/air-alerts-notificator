import os
from pathlib import Path

# Defaults to the repo root (one level above this package) so existing deployments
# that already have settings.db/session.session/events.db there keep working
# without any extra configuration. Override with ALERTBOT_DATA_DIR if needed.
DATA_DIR = Path(os.environ.get("ALERTBOT_DATA_DIR", Path(__file__).resolve().parent.parent))
