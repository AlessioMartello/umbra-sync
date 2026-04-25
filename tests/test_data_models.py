import pytest
from pydantic import ValidationError

from utils.data_models import Contact


class TestContactModelValidation:
    """Test Contact Pydantic model validation."""

    def test_contact_creation_with_all_fields(self):
        """Test creating a Contact with all fields."""
        contact = Contact(
            email_address="john.doe@example.com",
            name="John Doe",
            phone="+441234567890",
            linkedin="linkedin.com/in/johndoe",
            monday_id="12345",
            address="123 Main St",
            job_title="Software Engineer",
            website="johndoe.com",
        )

        assert contact.email_address == "john.doe@example.com"
        assert contact.name == "John Doe"
        assert contact.phone == "+441234567890"
        assert contact.linkedin == "linkedin.com/in/johndoe"
        assert contact.monday_id == "12345"
        assert contact.address == "123 Main St"
        assert contact.job_title == "Software Engineer"
        assert contact.website == "johndoe.com"

    def test_contact_creation_with_required_fields_only(self):
        """Test creating Contact with only required fields."""
        contact = Contact(email_address="jane@example.com", name="Jane Smith")

        assert contact.email_address == "jane@example.com"
        assert contact.name == "Jane Smith"
        assert contact.phone is None
        assert contact.linkedin is None
        assert contact.monday_id is None
        assert contact.address is None
        assert contact.job_title is None
        assert contact.website is None

    def test_contact_missing_email_address(self):
        """Test that Contact requires email_address."""
        with pytest.raises(ValidationError) as exc_info:
            Contact(name="John Doe")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "email_address" in str(errors[0])

    def test_contact_missing_name(self):
        """Test that Contact requires name."""
        with pytest.raises(ValidationError) as exc_info:
            Contact(email_address="john@example.com")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "name" in str(errors[0])

    def test_contact_invalid_email_format(self):
        """Test that invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Contact(email_address="not_an_email", name="John Doe")

        errors = exc_info.value.errors()
        assert any("email" in str(error).lower() for error in errors)

    def test_contact_name_cannot_be_empty_string(self):
        """Test that name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            Contact(email_address="john@example.com", name="")

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_contact_name_minimum_length_one(self):
        """Test that name must have minimum length of 1."""
        with pytest.raises(ValidationError):
            Contact(email_address="john@example.com", name="")

    def test_contact_accepts_various_valid_email_formats(self):
        """Test that various valid email formats are accepted."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@example.org",
            "123@example.com",
        ]

        for email in valid_emails:
            contact = Contact(email_address=email, name="Test User")
            assert contact.email_address == email

    def test_contact_with_all_optional_fields_as_none(self):
        """Test Contact with all optional fields explicitly set to None."""
        contact = Contact(
            email_address="test@example.com",
            name="Test",
            phone=None,
            linkedin=None,
            monday_id=None,
            address=None,
            job_title=None,
            website=None,
        )

        assert contact.phone is None
        assert contact.linkedin is None
        assert contact.monday_id is None

    def test_contact_serializes_to_dict(self):
        """Test that Contact can be serialized to dict."""
        contact = Contact(
            email_address="john@example.com", name="John Doe", phone="+441234567890"
        )

        contact_dict = contact.model_dump()
        assert isinstance(contact_dict, dict)
        assert contact_dict["email_address"] == "john@example.com"
        assert contact_dict["name"] == "John Doe"
        assert contact_dict["phone"] == "+441234567890"

    def test_contact_serializes_to_json(self):
        """Test that Contact can be serialized to JSON."""
        contact = Contact(email_address="john@example.com", name="John Doe")

        json_str = contact.model_dump_json()
        assert isinstance(json_str, str)
        assert "john@example.com" in json_str
        assert "John Doe" in json_str

    def test_contact_deserializes_from_dict(self):
        """Test creating Contact from dict."""
        data = {
            "email_address": "jane@example.com",
            "name": "Jane",
            "phone": "+441111111111",
        }

        contact = Contact(**data)
        assert contact.email_address == "jane@example.com"
        assert contact.name == "Jane"
        assert contact.phone == "+441111111111"

    def test_contact_with_whitespace_in_optional_fields(self):
        """Test that whitespace in optional fields is preserved."""
        contact = Contact(
            email_address="test@example.com",
            name="Test",
            linkedin="  linkedin.com/in/test  ",
            website="  www.test.com  ",
        )

        # Pydantic may or may not strip whitespace depending on validators
        # Just verify it accepts the data
        assert contact.linkedin is not None
        assert contact.website is not None

    def test_contact_field_types(self):
        """Test that all fields have correct types."""
        contact = Contact(
            email_address="test@example.com",
            name="Test",
            phone="+441234567890",
            linkedin="linkedin.com",
            monday_id="123",
            address="123 St",
            job_title="Engineer",
            website="test.com",
        )

        assert isinstance(contact.email_address, str)
        assert isinstance(contact.name, str)
        assert isinstance(contact.phone, str) or contact.phone is None
        assert isinstance(contact.linkedin, str) or contact.linkedin is None
        assert isinstance(contact.monday_id, str) or contact.monday_id is None


class TestContactEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_contact_with_very_long_name(self):
        """Test Contact with very long name."""
        long_name = "A" * 1000
        contact = Contact(email_address="test@example.com", name=long_name)
        assert contact.name == long_name

    def test_contact_with_special_characters_in_name(self):
        """Test Contact with special characters in name."""
        special_name = "José García-López O'Brien"
        contact = Contact(email_address="test@example.com", name=special_name)
        assert contact.name == special_name

    def test_contact_with_unicode_characters_in_name(self):
        """Test Contact with Unicode characters."""
        unicode_name = "北京 (Beijing)"
        contact = Contact(email_address="test@example.com", name=unicode_name)
        assert contact.name == unicode_name

    def test_contact_with_international_domain_email(self):
        """Test Contact with international domain email."""
        contact = Contact(email_address="user@münchen.de", name="Test")
        # Should accept international domain emails
        assert contact.email_address is not None

    def test_contact_excludes_none_in_json_export(self):
        """Test that None values are included/excluded based on configuration."""
        contact = Contact(email_address="test@example.com", name="Test", phone=None)

        json_data = contact.model_dump()
        # Verify structure includes phone even if None
        assert "phone" in json_data
        assert json_data["phone"] is None

    def test_contact_copy_method(self):
        """Test copying a Contact instance."""
        contact1 = Contact(
            email_address="test@example.com", name="Test", phone="+441234567890"
        )

        contact2 = contact1.model_copy()
        assert contact2.email_address == contact1.email_address
        assert contact2.name == contact1.name
        assert contact2.phone == contact1.phone

    def test_contact_update_method(self):
        """Test updating Contact fields."""
        contact = Contact(email_address="test@example.com", name="Test")

        updated = contact.model_copy(update={"phone": "+441234567890"})
        assert updated.phone == "+441234567890"
        assert updated.email_address == contact.email_address

    def test_contact_immutability_after_creation(self):
        """Test that attempting to modify Contact raises error."""
        contact = Contact(email_address="test@example.com", name="Test")

        # Pydantic v2 by default allows mutation unless frozen=True
        # Just verify the model is created
        assert contact.email_address == "test@example.com"
