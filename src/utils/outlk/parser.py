def filter_inbox(inbox_data: list, trusted_recipients: set[str]) -> list[dict]:
    """Returns only emails from senders that have been sent an email"""
    filtered_inbox = []
    for msg in inbox_data:
        sender_email = msg.get('from', {}).get('emailAddress', {}).get('address', '').lower().strip()

        if sender_email in trusted_recipients:
            filtered_inbox.append(msg)
        else:
            continue
    return filtered_inbox
        

def get_sent_recipient_emails(sent_data:list) -> set[str]:
    """Returns the email addresses of contacts that have been sent an email"""
    known_emails:set = set()
    for msg in sent_data:
        # Get the list of recipients and cc'd (defaults to empty list if none)
        recipients = msg.get('toRecipients', []) + msg.get('ccRecipients', [])
        
        # Loop through EVERY person in the 'To' line
        for recipient in recipients:
            email = recipient.get('emailAddress', {}).get('address', '').lower().strip()
            if email:
                known_emails.add(email)
    return known_emails