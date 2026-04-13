import pytest
from claudehooks.pii import PIIFilter


def test_pii_filter_creation():
    f = PIIFilter()
    assert f is not None


def test_anonymize_email():
    f = PIIFilter()
    text = "Contact me at john@example.com for details."
    anon, mapping = f.anonymize(text)
    assert "john@example.com" not in anon
    assert "EMAIL_" in anon
    assert len(mapping) > 0


def test_anonymize_phone():
    f = PIIFilter()
    text = "Call me at 555-123-4567 please."
    anon, mapping = f.anonymize(text)
    assert "555-123-4567" not in anon
    assert "PHONE_" in anon


def test_anonymize_ssn():
    f = PIIFilter()
    text = "My SSN is 123-45-6789."
    anon, mapping = f.anonymize(text)
    assert "123-45-6789" not in anon
    assert "SSN_" in anon


def test_deanonymize_restores():
    f = PIIFilter()
    text = "Email john@example.com and call 555-123-4567."
    anon, mapping = f.anonymize(text)
    restored = f.deanonymize(anon, mapping)
    assert "john@example.com" in restored
    assert "555-123-4567" in restored


def test_no_pii_returns_unchanged():
    f = PIIFilter()
    text = "This is a clean sentence with no PII."
    anon, mapping = f.anonymize(text)
    assert anon == text
    assert len(mapping) == 0


def test_multiple_same_type():
    f = PIIFilter()
    text = "Email alice@test.com and bob@test.com."
    anon, mapping = f.anonymize(text)
    assert "alice@test.com" not in anon
    assert "bob@test.com" not in anon
    assert "EMAIL_1" in anon
    assert "EMAIL_2" in anon


def test_deanonymize_with_empty_mapping():
    f = PIIFilter()
    text = "No tokens here."
    result = f.deanonymize(text, {})
    assert result == text


def test_anonymize_credit_card():
    f = PIIFilter()
    text = "Card number 4111-1111-1111-1111 on file."
    anon, mapping = f.anonymize(text)
    assert "4111-1111-1111-1111" not in anon
    assert "CREDIT_CARD_" in anon
