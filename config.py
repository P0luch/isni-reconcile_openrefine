import os
import sys

PORT = int(os.environ.get("PORT", 5100))

DEFAULT_MAX_RESULTS = 3
DEFAULT_THRESHOLD = 40.0

if getattr(sys, "frozen", False):
    # Mode exécutable PyInstaller : templates dans le bundle, données à côté de l'exe
    TEMPLATE_DIR = os.path.join(sys._MEIPASS, "templates")
    DATA_DIR     = os.path.join(os.path.dirname(sys.executable), "isni-reconcile-openrefine")
else:
    # Mode script Python direct
    _base        = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(_base, "templates")
    DATA_DIR     = _base

os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CACHE_FILE    = os.path.join(DATA_DIR, "isni_search_cache.pkl")
RECORD_FILE   = os.path.join(DATA_DIR, "isni_record_cache.pkl")
