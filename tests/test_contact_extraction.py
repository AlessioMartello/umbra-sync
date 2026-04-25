import pytest
import json
from unittest.mock import patch, Mock
from utils.contact_extraction import (
    _parse_email_body,
    _look_for_linkedin_address,
    _extract_phone_number,
    _get_email_tail,
    _nlp_signature_contact_extraction,
)


class TestParseEmailBody:
    """Test email body parsing from HTML."""

    def test_parse_simple_html_body(self):
        """Test parsing simple HTML email body."""
        email = {"uniqueBody": {"content": "<p>Hello World</p>"}}
        result = _parse_email_body(email)
        assert result == "Hello World"

    def test_parse_email_with_multiple_paragraphs(self):
        """Test parsing email with multiple paragraphs."""
        email = {
            "uniqueBody": {"content": "<p>First paragraph</p><p>Second paragraph</p>"}
        }
        result = _parse_email_body(email)
        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_parse_email_preserves_anchor_href_as_text(self):
        """Test that anchor href attributes are appended as text."""
        email = {
            "uniqueBody": {
                "content": '<a href="https://linkedin.com/in/johndoe">My Profile</a>'
            }
        }
        result = _parse_email_body(email)
        assert "My Profile" in result
        assert "https://linkedin.com/in/johndoe" in result

    def test_parse_email_collapses_whitespace(self):
        """Test that whitespace is normalized."""
        email = {"uniqueBody": {"content": "<p>Hello</p>\n\n\n<p>World</p>"}}
        result = _parse_email_body(email)
        assert "Hello" in result
        assert "World" in result
        # Verify multiple newlines are collapsed
        assert "\n\n" not in result

    def test_parse_email_strips_html_tags(self):
        """Test that HTML tags are removed."""
        email = {
            "uniqueBody": {
                "content": "<h1>Title</h1><strong>Bold text</strong><em>Italic</em>"
            }
        }
        result = _parse_email_body(email)
        assert "Title" in result
        assert "Bold text" in result
        assert "Italic" in result
        assert "<" not in result
        assert ">" not in result

    def test_parse_email_with_empty_body(self):
        """Test parsing email with empty body."""
        email = {"uniqueBody": {"content": ""}}
        result = _parse_email_body(email)
        assert result == ""

    def test_parse_email_missing_unique_body_key(self):
        """Test parsing email missing uniqueBody key."""
        email = {}
        result = _parse_email_body(email)
        assert result == ""

    def test_parse_email_missing_content_key(self):
        """Test parsing email with uniqueBody but no content."""
        email = {"uniqueBody": {}}
        result = _parse_email_body(email)
        assert result == ""

    def test_parse_email_with_complex_nested_html(self):
        """Test parsing complex nested HTML structure."""
        email = {
            "uniqueBody": {
                "content": "<div><table><tr><td>Data</td></tr></table></div>"
            }
        }
        result = _parse_email_body(email)
        assert "Data" in result


class TestLinkedinExtraction:
    """Test LinkedIn URL extraction from text."""

    def test_extract_linkedin_with_protocol_www(self):
        """Test extracting LinkedIn URL with https and www."""
        text = "Check out my profile: https://www.linkedin.com/in/johndoe/"
        result = _look_for_linkedin_address(text)
        assert "linkedin.com/in/johndoe" in result
        assert result.endswith("johndoe")

    def test_extract_linkedin_without_protocol(self):
        """Test extracting LinkedIn URL without protocol."""
        text = "My LinkedIn is linkedin.com/in/jane-smith"
        result = _look_for_linkedin_address(text)
        assert "linkedin.com/in/jane-smith" in result

    def test_extract_linkedin_strips_trailing_punctuation(self):
        """Test that trailing punctuation is removed."""
        text = "Visit linkedin.com/in/johndoe."
        result = _look_for_linkedin_address(text)
        assert result == "linkedin.com/in/johndoe"

    def test_extract_linkedin_with_query_parameters(self):
        """Test extracting LinkedIn URL with query parameters."""
        text = "linkedin.com/in/johndoe?trk=nav_responsive_tab_profile"
        result = _look_for_linkedin_address(text)
        assert "linkedin.com/in/johndoe" in result
        assert "trk=" in result

    def test_extract_linkedin_rejects_jobs_urls(self):
        """Test that LinkedIn jobs URLs are rejected."""
        text = "https://www.linkedin.com/jobs/view/123456/"
        result = _look_for_linkedin_address(text)
        assert result == ""

    def test_extract_linkedin_rejects_company_urls(self):
        """Test that LinkedIn company URLs are rejected."""
        text = "https://www.linkedin.com/company/acme/"
        result = _look_for_linkedin_address(text)
        assert result == ""

    def test_extract_linkedin_from_empty_string(self):
        """Test extraction from empty string."""
        result = _look_for_linkedin_address("")
        assert result == ""

    def test_extract_linkedin_returns_first_url_only(self):
        """Test that only first LinkedIn URL is returned."""
        text = "linkedin.com/in/johndoe and linkedin.com/in/janedoe"
        result = _look_for_linkedin_address(text)
        assert "johndoe" in result
        assert "janedoe" not in result

    def test_extract_linkedin_rejects_invalid_domain(self):
        """Test that non-LinkedIn domains are rejected."""
        text = "Check notlinkedin.com/in/johndoe"
        result = _look_for_linkedin_address(text)
        assert result == ""


class TestPhoneNumberExtraction:
    """Test phone number extraction."""

    def test_extract_valid_gb_phone_number(self):
        """Test extracting valid UK phone number."""
        text = "You can reach me at 020 7946 0958"
        result = _extract_phone_number(text)
        assert result.startswith("+44")  # E.164 format

    def test_extract_phone_formats_in_e164(self):
        """Test that phone numbers are formatted in E.164."""
        text = "Call me: 020 7946 0958"
        result = _extract_phone_number(text)
        assert result.startswith("+44")

    def test_extract_phone_returns_empty_for_invalid(self):
        """Test that invalid phone numbers return empty string."""
        text = "My number is 123"
        result = _extract_phone_number(text)
        assert result == ""

    def test_extract_phone_with_no_phone_in_text(self):
        """Test extraction with no phone numbers in text."""
        text = "Hello world, this is just text"
        result = _extract_phone_number(text)
        assert result == ""

    def test_extract_phone_returns_first_match(self):
        """Test that only first valid phone number is returned."""
        text = "Primary: 07700 900000 or Secondary: 020 7946 0958"
        result = _extract_phone_number(text)
        assert result is not None
        assert result.startswith("+44")


class TestEmailTailExtraction:
    """Test email tail extraction for signature processing."""

    def test_get_email_tail_returns_last_25_percent(self):
        """Test that last 3500 characters are extracted."""
        # Create email larger than 3500 chars
        long_text = "Start " + "x" * 4000 + " End"
        result = _get_email_tail(long_text)
        assert len(result) <= 3500
        assert "End" in result

    def test_get_email_tail_with_short_email(self):
        """Test extraction from email shorter than 3500 chars."""
        short_text = "Brief email"
        result = _get_email_tail(short_text)
        assert result == "Brief email"

    def test_get_email_tail_strips_whitespace(self):
        """Test that whitespace is stripped."""
        text = "   Content   \n\n"
        result = _get_email_tail(text)
        assert result == "Content"

    def test_get_email_tail_with_empty_string(self):
        """Test extraction from empty string."""
        result = _get_email_tail("")
        assert result == ""


class TestNlpSignatureExtraction:
    """Test NLP-based contact extraction from email signatures."""

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_returns_valid_json(self, mock_groq_client):
        """Test that NLP extraction returns parsed JSON."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "name": "John Doe",
                            "phone": "+441234567890",
                            "linkedin_url": "linkedin.com/in/johndoe",
                            "job_title": "Software Engineer",
                            "website": "johndoe.com",
                            "address": "123 Main St",
                        }
                    )
                )
            )
        ]
        mock_groq_client.chat.completions.create.return_value = mock_response

        result = _nlp_signature_contact_extraction(
            "Test email body", "john@example.com"
        )

        assert result["name"] == "John Doe"
        assert result["phone"] == "+441234567890"
        assert result["job_title"] == "Software Engineer"

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_with_null_fields(self, mock_groq_client):
        """Test extraction when some fields are null."""
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        {
                            "name": "Jane Smith",
                            "phone": None,
                            "linkedin_url": None,
                            "job_title": "Manager",
                            "website": None,
                            "address": None,
                        }
                    )
                )
            )
        ]
        mock_groq_client.chat.completions.create.return_value = mock_response

        result = _nlp_signature_contact_extraction("Test email", "jane@example.com")

        assert result["name"] == "Jane Smith"
        assert result["phone"] is None
        assert result["linkedin_url"] is None

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_handles_malformed_json(self, mock_groq_client):
        """Test extraction handles malformed JSON from Groq."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="This is not valid JSON"))]
        mock_groq_client.chat.completions.create.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):
            _nlp_signature_contact_extraction("Test email", "test@example.com")

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_calls_groq_with_correct_params(self, mock_groq_client):
        """Test that Groq API is called with correct model and parameters."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({})))]
        mock_groq_client.chat.completions.create.return_value = mock_response

        email_body = "Test signature"
        sender_email = "sender@example.com"

        _nlp_signature_contact_extraction(email_body, sender_email)

        # Verify create was called
        assert mock_groq_client.chat.completions.create.called
        call_args = mock_groq_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "llama-3.3-70b-versatile"

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_extracts_email_tail(self, mock_groq_client):
        """Test that only last 3500 chars are sent to Groq."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({})))]
        mock_groq_client.chat.completions.create.return_value = mock_response

        long_email = "Start" + "x" * 5000 + "End"
        _nlp_signature_contact_extraction(long_email, "test@example.com")

        # Verify the prompt was shortened
        call_args = mock_groq_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "End" in prompt
        assert "Start" not in prompt

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_includes_sender_email_in_prompt(self, mock_groq_client):
        """Test that sender email is included in the prompt."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps({})))]
        mock_groq_client.chat.completions.create.return_value = mock_response

        sender_email = "john.doe@acme.com"
        _nlp_signature_contact_extraction("Email body", sender_email)

        call_args = mock_groq_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert sender_email in prompt

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_with_retry_decorator(self, mock_groq_client):
        """Test that NLP extraction uses retry strategy."""
        from groq import RateLimitError

        # Simulate rate limit on first call, success on second
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({"name": "Test"})))
        ]
        mock_groq_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limited", response=Mock(), body=""),
            mock_response,
        ]

        result = _nlp_signature_contact_extraction("Test", "test@example.com")
        assert result["name"] == "Test"

    @patch("utils.contact_extraction.client")
    def test_nlp_extraction_returns_all_expected_fields(self, mock_groq_client):
        """Test that extraction returns all expected fields."""
        mock_response = Mock()
        expected_fields = {
            "name": "Alice Johnson",
            "phone": "+441111111111",
            "linkedin_url": "linkedin.com/in/alice",
            "job_title": "Director",
            "website": "alice.io",
            "address": "42 Baker Street",
        }
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps(expected_fields)))
        ]
        mock_groq_client.chat.completions.create.return_value = mock_response

        result = _nlp_signature_contact_extraction("Test", "alice@example.com")

        for field, value in expected_fields.items():
            assert result[field] == value
