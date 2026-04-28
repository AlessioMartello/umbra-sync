import re
from datetime import datetime, timezone

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
    logger.info("Getting known sender email addresses")

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


def deduplicate_inbox(inbox_data: list[dict], since: datetime = None) -> list[dict]:
    """Group emails by sender. Keep more on initial load, fewer on normal runs.

    Returns all emails but grouped — each sender's recent emails are preserved.
    """
    _check_list(inbox_data)

    sorted_emails = _sort_inbox(inbox_data)

    # Detect initial load: if watermark is > 30 days old
    is_initial_load = False
    if since:
        age = datetime.now(timezone.utc) - since
        is_initial_load = age.days > 30

    keep_per_sender = 10 if is_initial_load else 3

    logger.info(
        f"Deduplicating inbox (initial_load={is_initial_load}, keep_per_sender={keep_per_sender})"
    )
    logger.info(f"Before: {len(inbox_data)} emails")

    grouped = {}
    for msg in sorted_emails:
        sender_email = _get_email_address(msg)
        if sender_email:
            if sender_email not in grouped:
                grouped[sender_email] = []
            if len(grouped[sender_email]) < keep_per_sender:
                grouped[sender_email].append(msg)
        else:
            logger.warning("Skipping email with no sender during deduplication")

    result = [email for emails in grouped.values() for email in emails]
    logger.info(f"After: {len(result)} emails from {len(grouped)} senders")
    return result


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
    if len(email_body) < 20:
        logger.info("Email body too short for NLP extraction, skipping")
        nlp_extracted = {}
    else:
        nlp_extracted = _nlp_signature_contact_extraction(email_body, email_address)

    if nlp_extracted:
        name = name or nlp_extracted.get("name")
        phone = phone or nlp_extracted.get("phone")
        linkedin = linkedin or nlp_extracted.get("linkedin_url")
        job_title = nlp_extracted.get("job_title")
        website = nlp_extracted.get("website")
        address = nlp_extracted.get("address")

    return Contact(
        email_address=email_address,
        name=name,
        phone=phone,
        linkedin=linkedin,
        job_title=job_title,
        website=website,
        address=address,
    )


def merge_contacts_from_emails(emails: list[dict]) -> Contact:
    """Extract contacts from multiple emails and merge, prioritizing newest data.

    Most recent email is the base; older emails fill in missing fields.
    Returns partial contact if some extractions fail, but at least gets email address.
    """
    if not emails:
        raise ValueError("No emails provided for merging")

    contacts = []
    for email in emails:
        try:
            c = parse_email_to_contact(email)
            contacts.append(c)
        except Exception as e:
            logger.debug(f"Failed to extract contact from email: {e}")

    if not contacts:
        # Fallback: create minimal contact from email headers if extraction failed
        logger.warning(
            "No extractable contacts from email batch; creating minimal contact from headers"
        )
        email_address = _get_email_address(emails[0])
        name = _get_name(emails[0]) or email_address.split("@")[0]
        return Contact(email_address=email_address, name=name)

    # Start with newest contact, fill gaps from older ones
    merged = contacts[-1]
    logger.debug(
        f"Merging {len(contacts)} contacts for {merged.email_address}; base email #{len(contacts)} (newest)"
    )

    for contact in reversed(contacts[:-1]):
        for field in ["phone", "linkedin", "address", "website", "job_title"]:
            if not getattr(merged, field) and getattr(contact, field):
                new_value = getattr(contact, field)
                setattr(merged, field, new_value)
                logger.debug(f"  Filled {field}: {new_value} (from older email)")

    return merged


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
