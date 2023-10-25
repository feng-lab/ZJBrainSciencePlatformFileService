import os
import sys
from pathlib import Path

os.environ["ZJBS_FILE_DEBUG_MODE"] = "on"
sys.path.append(str(Path(__file__).parent.parent / "src"))
