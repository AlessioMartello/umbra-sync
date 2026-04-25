import pytest
from utils.transforms import (
    _look_for_linkedin_address,
    _parse_email_body,
    _get_email_address,
    _is_junk,
    _sort_inbox,
    _check_list,
    _check_set,
    _get_name,
)


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
    linkedin = _look_for_linkedin_address(input)
    assert linkedin == expected, f"Expected {expected} but got {linkedin}"


@pytest.mark.parametrize(
    "email, expected",
    [
        # --- Basic plain text body ---
        ({"uniqueBody": {"content": "<p>Hello world</p>"}}, "Hello world"),
        # --- Empty body ---
        ({"uniqueBody": {"content": ""}}, ""),
        # --- Missing body key ---
        ({}, ""),
        # --- Missing content key ---
        ({"uniqueBody": {}}, ""),
        # --- LinkedIn URL hidden in anchor tag text (core case) ---
        (
            {
                "uniqueBody": {
                    "content": '<a href="https://linkedin.com/in/johndoe">My Profile</a>'
                }
            },
            "My Profile https://linkedin.com/in/johndoe",
        ),
        # --- Anchor with URL as both text and href (URL should not be duplicated badly) ---
        (
            {
                "uniqueBody": {
                    "content": '<a href="https://linkedin.com/in/johndoe">https://linkedin.com/in/johndoe</a>'
                }
            },
            "https://linkedin.com/in/johndoe https://linkedin.com/in/johndoe",
        ),
        # --- Multiple anchor tags ---
        (
            {
                "uniqueBody": {
                    "content": '<a href="https://linkedin.com/in/johndoe">Profile</a> and <a href="https://example.com">Site</a>'
                }
            },
            "Profile https://linkedin.com/in/johndoe and Site https://example.com",
        ),
        # --- Anchor with no href (should be ignored) ---
        ({"uniqueBody": {"content": "<a>No href here</a>"}}, "No href here"),
        # --- Whitespace and newlines collapsed ---
        ({"uniqueBody": {"content": "<p>Hello</p>\n\n<p>World</p>"}}, "Hello World"),
        # --- Strips HTML tags ---
        (
            {
                "uniqueBody": {
                    "content": "<h1>Title</h1><p>Body <strong>text</strong></p>"
                }
            },
            "Title Body text",
        ),
        # --- Realistic email signature with hidden LinkedIn URL ---
        (
            {
                "uniqueBody": {
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
        (
            {"from": {"emailAddress": {"address": "john.doe@example.com"}}},
            "john.doe@example.com",
        ),
        (
            {"from": {"emailAddress": {"address": " jane.smith@example.com "}}},
            "jane.smith@example.com",
        ),
        ({"from": {"emailAddress": {}}}, ""),
        ({"from": {}}, ""),
        ({}, ""),
    ],
)
def test_email_extraction(email, expected):
    result = _get_email_address(email)
    assert result == expected, f"Expected '{expected}' but got '{result}'"


@pytest.mark.parametrize(
    "email_address, expected",
    [
        ("subscribe@example.com", True),
        ("thisisatestemailaddressismorethanfortycharacterslong@example.co.uk", True),
        ("john.doe@example.com", False),
        ("noreply@example.com", True),
        ("unsubscribe@example.com", True),
        ("bounce@example.com", True),
        ("", False),
    ],
)
def test_is_junk(email_address, expected):
    result = _is_junk(email_address)
    assert result == expected, f"Expected '{expected}' but got '{result}'"


def test_sort_inbox():
    data = [
        {"id": "test_value_a", "receivedDateTime": "2023-01-03T00:00:00Z"},
        {"id": "test_value_b", "receivedDateTime": "2023-01-01T00:00:00Z"},
        {"id": "test_value_c", "receivedDateTime": "2023-01-02T00:00:00Z"},
    ]
    result = _sort_inbox(data)

    assert len(result) == 3, f"Expected 3 items but got {len(result)}"
    assert (
        result[0]["id"] == "test_value_b"
    ), f"Expected 'test_value_b' but got '{result[0]['id']}'"
    assert (
        result[1]["id"] == "test_value_c"
    ), f"Expected 'test_value_c' but got '{result[1]['id']}'"
    assert (
        result[2]["id"] == "test_value_a"
    ), f"Expected 'test_value_a' but got '{result[2]['id']}'"


@pytest.mark.parametrize(
    "input, expected",
    [
        ("subscribe@example.com", True),
        (1, True),
        (set((1, 2, 3)), True),
        ((1, 2, 3), True),
        ([1, 2, 3], False),
        ([], False),
    ],
)
def test_check_list(input, expected):
    if expected:
        with pytest.raises(ValueError):
            _check_list(input)
    else:
        _check_list(input)  # Should not raise


@pytest.mark.parametrize(
    "input, expected",
    [
        ("subscribe@example.com", True),
        (1, True),
        (set((1, 2, 3)), False),
        ((1, 2, 3), True),
        ([1, 2, 3], True),
        ([], True),
    ],
)
def test_check_set(input, expected):
    if expected:
        with pytest.raises(ValueError):
            _check_set(input)
    else:
        _check_set(input)  # Should not raise


def test_get_name():
    email = {"from": {"emailAddress": {"name": " John Doe "}}}
    expected = "John Doe"
    result = _get_name(email)
    assert result == expected, f"Expected '{expected}' but got '{result}'"
