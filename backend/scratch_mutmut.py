import os
import sys

sys.path.insert(0, os.path.abspath(".venv/lib/python3.12/site-packages"))

from mutmut.__main__ import load_config

cfg = load_config()
print("paths_to_mutate:", cfg.paths_to_mutate)
