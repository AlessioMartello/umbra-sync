from utils.outlk.client import OutlookClient
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

async def main():
    async with OutlookClient(client_id=CLIENT_ID, refresh_token=REFRESH_TOKEN) as outlook:
        res = await outlook.get_inbox_items()
        print(res)

if __name__ == "__main__":
    asyncio.run(main())