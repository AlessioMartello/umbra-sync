import pytest
from utils.transforms import _look_for_linkedin_address, _parse_email_body, _get_email_address


@pytest.mark.parametrize(
    "input, expected",
    [
        ("https://www.linkedin.com/in/johndoe/", "https://www.linkedin.com/in/johndoe"),
        ("No LinkedIn URL here", ""),
        (
            "Check out my profile: http://www.linkedin.com/in/janedoe/ ",
            "http://www.linkedin.com/in/janedoe",
        ),
        ("Not a persons URL https://www.linkedin.com/johndoe", ""),
        ("No protocal www.linkedin.com/in/johndoe/", "www.linkedin.com/in/johndoe"),
        ("linkedin.com/in/johndoe/", "linkedin.com/in/johndoe"),
        # --- Trailing punctuation ---
        ("linkedin.com/in/johndoe.", "linkedin.com/in/johndoe"),
        ("linkedin.com/in/johndoe,", "linkedin.com/in/johndoe"),
        ("(linkedin.com/in/johndoe)", "linkedin.com/in/johndoe"),
        ("linkedin.com/in/johndoe!", "linkedin.com/in/johndoe"),
        # --- Angle brackets (raw email format) ---
        ("<https://linkedin.com/in/johndoe>", "https://linkedin.com/in/johndoe"),
        ("<linkedin.com/in/johndoe>", "linkedin.com/in/johndoe"),
        # --- Query strings / tracking params ---
        (
            "linkedin.com/in/johndoe?trk=nav_responsive_tab_profile",
            "linkedin.com/in/johndoe?trk=nav_responsive_tab_profile",
        ),
        # --- Slugs with hyphens and numbers ---
        ("linkedin.com/in/john-doe-123456789/", "linkedin.com/in/john-doe-123456789"),
        ("linkedin.com/in/j0hn-d0e/", "linkedin.com/in/j0hn-d0e"),
        # --- Embedded in sentence ---
        (
            "My profile is linkedin.com/in/johndoe feel free to connect",
            "linkedin.com/in/johndoe",
        ),
        (
            "Visit https://linkedin.com/in/johndoe for more info.",
            "https://linkedin.com/in/johndoe",
        ),
        # --- Case insensitivity ---
        ("HTTPS://WWW.LINKEDIN.COM/IN/JOHNDOE/", "HTTPS://WWW.LINKEDIN.COM/IN/JOHNDOE"),
        # --- False positives to reject ---
        ("https://www.linkedin.com/jobs/view/123456", ""),  # /jobs/ not /in/
        ("https://www.linkedin.com/company/acme/", ""),  # /company/ not /in/
        ("notlinkedin.com/in/johndoe", ""),  # fake domain
        ("https://linkedin.com/in/", ""),  # empty slug
        ("", ""),  # empty string
        # --- Multiple URLs (should return first) ---
        (
            "linkedin.com/in/johndoe and linkedin.com/in/janedoe",
            "linkedin.com/in/johndoe",
        ),
    ],
)
def test_linkedin_parsing(input, expected):
    """Tests many permutations. Core functionality must be robust."""
    linkedin_url = _look_for_linkedin_address(input)
    assert linkedin_url == expected, f"Expected {expected} but got {linkedin_url}"


@pytest.mark.parametrize(
    "email, expected",
    [
        # --- Basic plain text body ---
        ({"body": {"content": "<p>Hello world</p>"}}, "Hello world"),
        # --- Empty body ---
        ({"body": {"content": ""}}, ""),
        # --- Missing body key ---
        ({}, ""),
        # --- Missing content key ---
        ({"body": {}}, ""),
        # --- LinkedIn URL hidden in anchor tag text (core case) ---
        (
            {
                "body": {
                    "content": '<a href="https://linkedin.com/in/johndoe">My Profile</a>'
                }
            },
            "My Profile https://linkedin.com/in/johndoe",
        ),
        # --- Anchor with URL as both text and href (URL should not be duplicated badly) ---
        (
            {
                "body": {
                    "content": '<a href="https://linkedin.com/in/johndoe">https://linkedin.com/in/johndoe</a>'
                }
            },
            "https://linkedin.com/in/johndoe https://linkedin.com/in/johndoe",
        ),
        # --- Multiple anchor tags ---
        (
            {
                "body": {
                    "content": '<a href="https://linkedin.com/in/johndoe">Profile</a> and <a href="https://example.com">Site</a>'
                }
            },
            "Profile https://linkedin.com/in/johndoe and Site https://example.com",
        ),
        # --- Anchor with no href (should be ignored) ---
        ({"body": {"content": "<a>No href here</a>"}}, "No href here"),
        # --- Whitespace and newlines collapsed ---
        ({"body": {"content": "<p>Hello</p>\n\n<p>World</p>"}}, "Hello World"),
        # --- Strips HTML tags ---
        (
            {"body": {"content": "<h1>Title</h1><p>Body <strong>text</strong></p>"}},
            "Title Body text",
        ),
        # --- Realistic email signature with hidden LinkedIn URL ---
        (
            {
                "body": {
                    "content": "<p>Best regards,</p><p>John</p><a href='https://linkedin.com/in/johndoe'>Connect on LinkedIn</a>"
                }
            },
            "Best regards, John Connect on LinkedIn https://linkedin.com/in/johndoe",
        ),
    ],
)
def test_parse_email_body(email, expected):
    result = _parse_email_body(email)
    assert result == expected, f"Expected '{expected}' but got '{result}'"


@pytest.mark.parametrize(
    "email, expected",
    [
        ({"from": {"emailAddress": {"address": "john.doe@example.com"}}}, "john.doe@example.com"),
        ({"from": {"emailAddress": {"address": " jane.smith@example.com "}}}, "jane.smith@example.com"),
        ({"from": {"emailAddress": {}}}, ""),
        ({"from": {}}, ""),
        ({}, ""),
    ],
)
def test_email_extraction(email, expected):
    result = _get_email_address(email)
    assert result == expected, f"Expected '{expected}' but got '{result}'"