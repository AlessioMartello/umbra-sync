from utils.data_models import Contact
from utils.logger import get_logger
from bs4 import BeautifulSoup

logger = get_logger(__name__)


def filter_inbox(inbox_data: list, trusted_recipients: set[str]) -> list[dict]:
    """Returns only emails from senders that have been sent an email"""
    _check_list(inbox_data)
    _check_set(trusted_recipients) 
  
    filtered_inbox = []
    logger.info(
        "Filtering out inbox for senders that have been emailed by this mailbox"
    )
    logger.info(f"Before filter: {len(inbox_data)} emails")
    for msg in inbox_data:
            sender_email = (
                msg.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
                .strip()
            )

            if sender_email in trusted_recipients:
                filtered_inbox.append(msg)

            else:
                logger.debug(f"Skipping inbox item {msg}")

    logger.info(f"After filter: {len(filtered_inbox)} emails")
    return filtered_inbox


def get_sent_recipient_emails(sent_data: list) -> set[str]:
    """Returns the email addresses of contacts that have been sent an email"""
    logger.info(f"Getting known sender email addresses")
    
    _check_list(sent_data)

    known_emails: set = set()
    for msg in sent_data:
            # Get the list of recipients and cc'd (defaults to empty list if none)
            recipients = msg.get("toRecipients", []) + msg.get("ccRecipients", [])

            # Loop through EVERY person in the 'To' line
            for recipient in recipients:
                email = recipient.get("emailAddress", {}).get("address", "").strip()
                if email:
                    known_emails.add(email)
                else:
                    logger.warning(f"Skipping sent item {msg}")

    logger.info(f"Obtained {len(known_emails)} trusted email addresses")

    return known_emails


def _sort_inbox(inbox_data: list[dict]):
    """Sorts the emails by data received"""
    return sorted(inbox_data, key=lambda x: x.get("receivedDateTime", ""))


def deduplicate_inbox(inbox_data: list[dict]) -> list[dict]:
    """Returns the latest email only from each sender"""
    _check_list(inbox_data)
    
    sorted_emails = _sort_inbox(inbox_data)
    logger.info("Deduplicating inbox items per sender")
    logger.info(f"Before deduplication: {len(inbox_data)} emails")

    deduplicated_dict = {}
    
    for msg in sorted_emails:
            sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").strip()
            if sender_email:
                deduplicated_dict[sender_email] = msg
            else:
                logger.warning(f"Skipping email {msg} during deduplication")
    
    deduplicated_items = list(deduplicated_dict.values())
    logger.info(f"After deduplication: {len(deduplicated_items)} emails")
    return deduplicated_items


def parse_email_to_contact(email: dict) -> Contact:
    """Take an email and return a Contact"""
    email_address: str
    name: str = None
    phone: str = None
    address: str = None

    sender = email.get("from", {}).get("emailAddress", {})
    email_address = sender.get("address", "").strip()
    name = sender.get("name", "").strip()
    
    if not email_address:
        raise ValueError("Email has no mandatory sender address")
    
    return Contact(email_address=email_address, name=name)



def parse_email_body(email: dict) -> str:
    """Reads HTML body and outputs as a string"""
    html_body = email.get("body", {}).get("content", "")
    soup = BeautifulSoup(html_body, "html.parser")
    text = soup.get_text(separator="\n")
    logger.info(f"Parsed email body to text: {text[:100]}...")  # Log the first 100 characters
    return text

def look_for_linkedin_address(email_body:str) -> str:
    ...

def _check_list(data: list) -> None:
    if not isinstance(data, list):
        logger.error(f"Expected data to be a list, got {type(data)}")
        raise ValueError("Invalid data format")
    
def _check_set(data:list) -> None:
    if not isinstance(data, set):
        logger.error(f"Expected data to be a set, got {type(data)}")
        raise ValueError("Invalid data format")