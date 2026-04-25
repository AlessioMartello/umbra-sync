import os
from pathlib import Path
from datetime import datetime


def write_job_summary(created: int, updated: int, skipped: int, since: str) -> None:
    summary = f"""
    #### Contacts sync summary ####
    | Metric | Value |
    |--------|-------|
    | Run at | {datetime.now().strftime("%Y-%m-%d %H:%M")} |
    | Watermark | {since} |
    | Created | {created} |
    | Updated | {updated} |
    | Skipped | {skipped} |
    | Total processed | {created + updated + skipped} |
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        summary_file = Path(summary_path)
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(summary)
