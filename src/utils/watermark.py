import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
WATERMARK_PATH = BASE_DIR / ".state" / "last_run.json"
DEBUG_LOOKBACK_DAYS = 2 * 365


def get_watermark(debug: bool) -> datetime:
    """Read the latest time that the script ran"""
    if not debug:
        if WATERMARK_PATH.exists():
            try:
                data = json.loads(WATERMARK_PATH.read_text())
                last_run = data["last_run"]
                logger.info(f"Latest watermark is: {last_run}")
                return datetime.fromisoformat(last_run)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(
                    f"Watermark file corrupt or invalid: {e} — defaulting to 365 days ago"
                )
                return datetime.now(timezone.utc) - timedelta(days=365)
        else:
            logger.warning("No watermark found — defaulting to 365 days ago")
            return datetime.now(timezone.utc) - timedelta(days=365)
    else:
        logger.info(f"Debug mode — looking back {DEBUG_LOOKBACK_DAYS} days")
        return datetime.now(timezone.utc) - timedelta(days=DEBUG_LOOKBACK_DAYS)


def update_watermark(debug) -> None:
    """Set the watermark to be the present timestamp"""
    if not debug:
        try:
            WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(timezone.utc).isoformat()
            WATERMARK_PATH.write_text(json.dumps({"last_run": now}))
            logger.info(f"Successfully updated watermark as {now}")
        except OSError as e:
            logger.error(f"Failed to write watermark: {e}")
            raise
    else:
        logger.info("Debug mode, ignoring watermark")
