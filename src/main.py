from utils.outlk.client import OutlookClient
from utils.outlk import parser
from dotenv import load_dotenv
import os
import asyncio

from datetime import datetime, timedelta, timezone

from utils.data_models import Contact
from utils.mday.client import MondayClient

now = datetime.now(timezone.utc)
one_year_ago = now - timedelta(days=20)

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
API_KEY = os.getenv("MONDAY_API_KEY")

async def main():
    async with OutlookClient(client_id=CLIENT_ID, refresh_token=REFRESH_TOKEN) as outlook:
        inbox, sent = await asyncio.gather(
            outlook.get_inbox_items(since=one_year_ago),
            outlook.get_sent_items(),
        )

    trusted_email_addresses = parser.get_sent_recipient_emails(sent)
    filtered_inbox = parser.filter_inbox(inbox, trusted_email_addresses)
    deduplicated_inbox = parser.deduplicate_inbox(filtered_inbox)

    async with MondayClient(API_KEY, "5094265847") as mday:
        contacts = await asyncio.gather(mday.get_existing_contacts())

        res = await mday.post_new_contacts(new_person)
    
    # Get the adresses 
    # Get the numbers
    # Get the name

if __name__ == "__main__":
    asyncio.run(main())