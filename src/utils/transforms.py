import re

from utils.data_models import Contact
from utils.logger import get_logger
from utils.contact_extraction import (
    _parse_email_body,
    _look_for_linkedin_address,
    _extract_phone_number,
    _nlp_signature_contact_extraction,
)

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
        sender_email = _get_email_address(msg)

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
            if email and not _is_junk(email):
                known_emails.add(email)
            else:
                logger.debug(f"Skipping sent item {email}")

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
        sender_email = _get_email_address(msg)
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
    linkedin: str = None

    email_address = _get_email_address(email)
    email_body = _parse_email_body(email)
    if not email_address:
        raise ValueError("Email has no mandatory sender address")

    ## Manual extraction
    name = _get_name(email) or email_address.split("@")[0]
    phone = _extract_phone_number(email_body)
    linkedin = _look_for_linkedin_address(email_body)

    ## NLP extraction
    nlp_extracted = _nlp_signature_contact_extraction(email_body, email_address)
    name = name or nlp_extracted.name
    phone = phone or nlp_extracted.phone
    linkedin = linkedin or nlp_extracted.linkedin
    job_title = nlp_extracted.job_title
    website = nlp_extracted.website
    address = nlp_extracted.address

    return Contact(
        email_address=email_address, name=name, phone=phone, linkedin=linkedin
    )


def _check_list(data: list) -> None:
    if not isinstance(data, list):
        logger.error(f"Expected data to be a list, got {type(data)}")
        raise ValueError("Invalid data format")


def _check_set(data: list) -> None:
    if not isinstance(data, set):
        logger.error(f"Expected data to be a set, got {type(data)}")
        raise ValueError("Invalid data format")


def _get_email_address(email: dict) -> str:
    """Extracts the sender's email address from the email dict"""
    return email.get("from", {}).get("emailAddress", {}).get("address", "").strip()


def _get_name(email: dict) -> str:
    """Extracts the sender's name from the email dict"""
    return email.get("from", {}).get("emailAddress", {}).get("name", "").strip()


def _is_junk(email: str) -> bool:
    """Leniant check if the email is from a junk sender"""
    JUNK_PATTERN = r"unsub|subscribe|bounce|noreply|no-reply|donotreply"

    if len(email) > 40:
        return True
    if re.search(JUNK_PATTERN, email, re.IGNORECASE):
        return True
    return False
