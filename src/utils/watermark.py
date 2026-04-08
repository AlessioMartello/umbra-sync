import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
WATERMARK_PATH = BASE_DIR / ".state" / "last_run.json"


def get_watermark(debug: bool) -> datetime:
    if not debug:
        if WATERMARK_PATH.exists():
            data = json.loads(WATERMARK_PATH.read_text())
            last_run = data["last_run"]
            logger.warning(f"Latest watermark is: {last_run}")
            return datetime.fromisoformat(last_run)
        else:
            logger.warning("No watermark file is present")
    else:
        logger.info("Debug mode, taking local configuration")
        return datetime.now(timezone.utc) - timedelta(days=20)


def update_watermark(debug) -> None:
    if not debug:
        WATERMARK_PATH.parent.mkdir(exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        WATERMARK_PATH.write_text(json.dumps({"last_run": now}))
        logger.info(f"Successfully updated watermark as {now}")
    else:
        logger.info("Debug mode, ignoring watermark")
