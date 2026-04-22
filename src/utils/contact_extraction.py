import re
import json
import os

from bs4 import BeautifulSoup
import phonenumbers
from groq import Groq
from dotenv import load_dotenv

from utils.logger import get_logger
from utils.retry_strategy import groq_retry_strategy


logger = get_logger(__name__)

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _parse_email_body(email: dict) -> str:
    """Reads HTML body and outputs as a string. Don't discard the href from anchor tags as LinkedIn URLs can be hidden inside them"""
    html_body = email.get("uniqueBody", {}).get("content", "")
    soup = BeautifulSoup(html_body, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        tag.append(f" {href} ")

    text = soup.get_text(separator=" ")
    text = " ".join(text.split())
    logger.debug(
        f"Parsed email body to text: {text[:100]}..."
    )  # Log the first 100 characters
    return text


def _look_for_linkedin_address(email_body: str) -> str:
    email_body = email_body.replace("<", " ").replace(">", " ")
    pattern = r"""
        (?:https?://)?          # optional protocol
        (?:www\.)?              # optional www only (avoids matching fakelinkedin.com)
        (?<![\w-])                  # no word char/hyphen directly before (blocks notlinkedin)
        linkedin\.com
        /in/
        [\w\-\.%]+             # profile slug
        (?:[/?][\w\-\.?=&%/]*)?    # optional query string or trailing path
    """
    match = re.search(pattern, email_body, re.IGNORECASE | re.VERBOSE)

    if match:
        linkedin = match.group(0).strip().rstrip(".,!?;:/")
        logger.debug(f"Found LinkedIn URL: {linkedin}")
        return linkedin
    return ""


def _extract_phone_number(email_body: str) -> str:
    matches = phonenumbers.PhoneNumberMatcher(email_body, "GB")
    for match in matches:
        number = match.number
        if phonenumbers.is_valid_number(number):
            return phonenumbers.format_number(
                number, phonenumbers.PhoneNumberFormat.E164
            )
    return ""

def _get_email_tail(email_body: str) -> str:
    """Extract the last 25% of the email body, where signatures usually are"""
    return email_body[-3500:].strip()


@groq_retry_strategy
def _nlp_signature_contact_extraction(email_body: str, sender_email: str) -> dict:
    email_body = _get_email_tail(email_body)

    prompt = f"""
    Extract contact information from this email signature.
    Only extract what is explicitly written — return null if not present.
    Return ONLY valid JSON, no other text:
    
    {{
        "name": null,
        "phone": null,
        "linkedin_url": null,
        "job_title": null,
        "website": null,
        "address": null
    }}
    
    Sender email (already known): {sender_email}
    
    EMAIL:
    {email_body}
    """

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},  # guarantees valid JSON back
        temperature=0,  # no creativity — just extract facts
    )

    return json.loads(response.choices[0].message.content) or {}
