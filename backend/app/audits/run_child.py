import json
import sys
from pathlib import Path
from app.audits.engine import compare
from app.documents.sandbox import restrict

if __name__ == "__main__":
    try:
        restrict()
        payload = json.loads(Path(sys.argv[1]).read_text())
        print(json.dumps({"ok": True, **compare(**payload)}))
    except BaseException:
        print(json.dumps({"ok": False, "error": "engine_failed"}))
