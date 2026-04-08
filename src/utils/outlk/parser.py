from utils.data_models import Contact
from utils.logger import get_logger

logger = get_logger(__name__)


def filter_inbox(inbox_data: list, trusted_recipients: set[str]) -> list[dict]:
    """Returns only emails from senders that have been sent an email"""
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
            .lower()
            .strip()
        )

        if sender_email in trusted_recipients:
            filtered_inbox.append(msg)
        else:
            continue
    logger.info(f"After filter: {len(filtered_inbox)} emails")
    return filtered_inbox


def get_sent_recipient_emails(sent_data: list) -> set[str]:
    """Returns the email addresses of contacts that have been sent an email"""
    logger.info(f"Getting known sender email addresses")
    known_emails: set = set()
    for msg in sent_data:
        # Get the list of recipients and cc'd (defaults to empty list if none)
        recipients = msg.get("toRecipients", []) + msg.get("ccRecipients", [])

        # Loop through EVERY person in the 'To' line
        for recipient in recipients:
            email = recipient.get("emailAddress", {}).get("address", "").lower().strip()
            if email:
                known_emails.add(email)
    logger.info(f"Obtained {len(known_emails)} trusted email addresses")
    return known_emails


def _sort_inbox(inbox_data: list[dict]):
    """Sorts the emails by data received"""
    return sorted(inbox_data, key=lambda x: x["receivedDateTime"])


def deduplicate_inbox(inbox_data: list[dict]):
    "Returns the latest email only from each sender"
    sorted_emails = _sort_inbox(inbox_data)
    logger.info(f"Deduplicating inbox items per sender")
    logger.info(f"Before deduplication: {len(inbox_data)} emails")

    deduplicated_items = list(
        {
            msg.get("from", {}).get("emailAddress", {}).get("address"): msg
            for msg in sorted_emails
        }.values()
    )
    logger.info(f"After deduplication: {len(deduplicated_items)} emails")

    return deduplicated_items


def parse_email_to_contact(email: dict) -> Contact:
    """Take an email and return a Contact"""
    email_address: str
    name: str = None
    phone: str = None
    address: str = None

    try:
        sender = email.get("from", {}).get("emailAddress", {})
        email_address = sender.get("address", {})
        name = sender.get("name", {})
        return Contact(email_address=email_address, name=name)
    except Exception as e:
        logger.error(f"Error extracting contact information from email: {e}")
        return None
