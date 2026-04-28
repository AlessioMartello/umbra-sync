import os
import asyncio
import argparse
from typing import Optional

from dotenv import load_dotenv

from clients.mday import MondayClient
from utils.logger import get_logger
from utils.watermark import get_watermark, update_watermark
from clients.outlk import OutlookClient
from utils import transforms
from utils.monitoring import write_job_summary
from utils.data_models import Contact

logger = get_logger(__name__)

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")
MONDAY_FIELDS_TO_CHECK = [
    "phone",
    "linkedin",
    "address",
    "job_title",
    "website",
]
RATE_LIMIT_DELAY = int(os.getenv("RATE_LIMIT_DELAY", "15"))

debug: bool = os.getenv("DEBUG", "False").strip().lower() in {"true"}
dry_run: bool = False


def _validate_env() -> None:
    """Validate all required environment variables at startup."""
    required_vars = [
        "AZURE_CLIENT_ID",
        "REFRESH_TOKEN",
        "MONDAY_API_KEY",
        "MONDAY_BOARD_ID",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please check your .env file."
        )
    logger.info("Environment variables validated")


async def main(dry_run_mode: bool = False) -> None:
    global dry_run
    dry_run = dry_run_mode

    _validate_env()
    logger.info(f"Script commencing (dry_run={dry_run})")
    logger.info("Getting latest watermark")
    since = get_watermark(debug)
    try:
        async with OutlookClient(
            client_id=CLIENT_ID, refresh_token=REFRESH_TOKEN
        ) as outlook:
            inbox, sent = await asyncio.gather(
                outlook.get_inbox_items(since=since),
                outlook.get_sent_items(),
            )

        trusted_email_addresses = transforms.get_sent_recipient_emails(sent)
        filtered_inbox = transforms.filter_inbox(inbox, trusted_email_addresses)
        deduplicated_inbox = transforms.deduplicate_inbox(filtered_inbox, since=since)

        to_create, to_update, skipped = [], [], []

        if len(deduplicated_inbox) > 0:
            logger.info(
                f"Preparing data for synchronisation with Monday.com ({len(deduplicated_inbox)} items to process)"
            )

            # Group emails by sender and merge per-sender contacts
            emails_by_sender = {}
            for email in deduplicated_inbox:
                sender = transforms._get_email_address(email)
                if sender not in emails_by_sender:
                    emails_by_sender[sender] = []
                emails_by_sender[sender].append(email)

            logger.info(f"Processing {len(emails_by_sender)} unique senders")

            async with MondayClient(API_KEY, MONDAY_BOARD_ID) as mday:
                mday_contacts = await mday.get_existing_contacts()

                for email_list in emails_by_sender.items():
                    outlook_contact: Optional[Contact] = None
                    try:
                        outlook_contact = transforms.merge_contacts_from_emails(
                            email_list
                        )

                        # Matching logic on email
                        existing_mday_contact = mday_contacts.get(
                            outlook_contact.email_address, None
                        )

                        # Add for creation
                        if not existing_mday_contact:
                            to_create.append(outlook_contact)
                            continue

                        # Check for updates coming from Outlook
                        missing_fields = {
                            field: getattr(outlook_contact, field)
                            for field in MONDAY_FIELDS_TO_CHECK
                            if getattr(outlook_contact, field)
                            and getattr(outlook_contact, field)
                            != getattr(existing_mday_contact, field)
                        }

                        # Mapping due to naming in Monday differing from our Contact model
                        if missing_fields:
                            to_update.append(
                                (existing_mday_contact.monday_id, missing_fields)
                            )

                        else:
                            skipped.append(outlook_contact)

                        await asyncio.sleep(
                            RATE_LIMIT_DELAY
                        )  # Proactive rate limiting for groq tokens

                    except Exception as e:
                        # This ensures one bad email doesn't crash the whole script
                        logger.warning(f"Skipping email due to processing error: {e}")
                        if outlook_contact:
                            skipped.append(outlook_contact)
                        continue

                # Execute the desired API actions in Monday
                logger.info(f"Creating {len(to_create)} contacts")
                if not dry_run:
                    for contact in to_create:
                        await mday.post_new_contact(contact)
                else:
                    logger.info("[DRY RUN] Skipping contact creation")

                logger.info(f"Updating {len(to_update)} contacts")
                if not dry_run:
                    for monday_id, fields in to_update:
                        await mday.update_contact(monday_id, fields)
                else:
                    logger.info("[DRY RUN] Skipping contact updates")

                logger.info(
                    f"sync_complete. Created: {len(to_create)}, Updated: {len(to_update)}, Skipped: {len(skipped)}"
                )
        else:
            logger.info("No new inbox data to process. exiting")

        # Get the numbers
        write_job_summary(len(to_create), len(to_update), len(skipped), since)
        if not dry_run:
            update_watermark(debug)
        else:
            logger.info("[DRY RUN] Skipping watermark update")

    except Exception as e:
        logger.exception(f"Script return an error: {e}")
        raise

    logger.info("Script completed with no errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Umbra Sync: Outlook to Monday.com contact synchronizer"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (overrides DEBUG env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to Monday.com",
    )
    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "true"
        debug = True

    asyncio.run(main(dry_run_mode=args.dry_run))
