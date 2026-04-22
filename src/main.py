import os
import asyncio

from dotenv import load_dotenv

from clients.mday import MondayClient
from utils.logger import get_logger
from utils.watermark import get_watermark, update_watermark
from clients.outlk import OutlookClient
from utils import transforms
from utils.monitoring import write_job_summary

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

debug: bool = os.getenv("DEBUG", "False").strip().lower() in {"true"}


async def main():
    logger.info("Script commencing")
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
        deduplicated_inbox = transforms.deduplicate_inbox(filtered_inbox)

        to_create, to_update, skipped = [], [], []

        if len(deduplicated_inbox) > 0:
            logger.info(f"Preparing data for synchronisation with Monday.com ({len(deduplicated_inbox)} items to process)")
            async with MondayClient(API_KEY, MONDAY_BOARD_ID) as mday:
                mday_contacts = await mday.get_existing_contacts()

                for email in deduplicated_inbox:
                    try:
                        outlook_contact = transforms.parse_email_to_contact(email)

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
                            and getattr(outlook_contact, field) != getattr(existing_mday_contact, field)
                        }

                        # Mapping due to naming in Monday differing from our Contact model
                        if missing_fields:
                            to_update.append(
                                (existing_mday_contact.monday_id, missing_fields)
                            )

                        else:
                            skipped.append(outlook_contact)

                        await asyncio.sleep(15) # Proactive rate limiting for groq tokens

                    except Exception as e:
                        # This ensures one bad email doesn't crash the whole script
                        logger.warning(f"Skipping email due to processing error: {e}")
                        skipped.append(outlook_contact)
                        continue

                # Execute the desired API actions in Monday
                logger.info(f"Creating {len(to_create)} contacts")
                for contact in to_create:
                    await mday.post_new_contact(contact)

                logger.info(f"Updating {len(to_update)} contacts")
                for monday_id, fields in to_update:
                    await mday.update_contact(monday_id, fields)

                logger.info(
                    f"sync_complete. Created: {len(to_create)}, Updated: {len(to_update)}, Skipped: {len(skipped)}"
                )
        else:
            logger.info("No new inbox data to process. exiting")

        # Get the numbers
        write_job_summary(len(to_create), len(to_update), len(skipped), since)
        update_watermark(debug)

    except Exception as e:
        logger.exception(f"Script return an error: {e}")
        raise

    logger.info("Script completed with no errors")


if __name__ == "__main__":
    asyncio.run(main())
