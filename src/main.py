import os
import asyncio
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from utils.mday.client import MondayClient
from utils.logger import get_logger
from utils.watermark import get_watermark, update_watermark
from utils.outlk.client import OutlookClient
from utils.outlk import parser

logger = get_logger(__name__)

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")

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

        trusted_email_addresses = parser.get_sent_recipient_emails(sent)
        filtered_inbox = parser.filter_inbox(inbox, trusted_email_addresses)
        deduplicated_inbox = parser.deduplicate_inbox(filtered_inbox)

        if len(deduplicated_inbox) > 0:
            async with MondayClient(API_KEY, MONDAY_BOARD_ID) as mday:
                contacts = await mday.get_existing_contacts()

                for email in deduplicated_inbox:
                    try:
                        # Any error in ANY of these steps triggers the 'except' block
                        contact = parser.parse_email_to_contact(email)
                                                
                        # await mday.post_new_contact(contact)
                        logger.info(f"Processed: {contact.email_address}")

                    except Exception as e:
                        # This ensures one bad email doesn't crash the whole script
                        logger.warning(f"Skipping email due to processing error: {e}")
                        continue

        else:
            logger.info("No new inbox data to process. exiting")

        # get linkedin
        # Get the numbers
        # Get the name

        # if email address in monday contact and missing data, enrich
        # if email address not in monday contacts, add
        # if email in monday contact and not missing data, no nothing
        
        update_watermark(debug)
    except Exception as e:
        logger.exception(f"Script return an error: {e}")
        raise

    logger.info("Script completed with no errors")


if __name__ == "__main__":
    asyncio.run(main())
