import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("ALERTBOT_DATA_DIR", Path(__file__).resolve().parent.parent))
