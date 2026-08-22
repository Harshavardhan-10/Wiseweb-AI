"""Unit tests: URL normalization."""

import pytest

from app.core.exceptions import ValidationError
from app.utils.urls import domain_of, normalize_url


def test_normalize_adds_scheme():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_preserves_path():
    assert normalize_url("https://example.com/about") == "https://example.com/about"


def test_normalize_lowercases_host():
    assert normalize_url("https://EXAMPLE.com/About") == "https://example.com/About"


def test_normalize_removes_fragment_and_strips_trailing_slash():
    assert normalize_url("https://example.com/") == "https://example.com/"
    assert normalize_url("https://example.com/a/#section") == "https://example.com/a"


def test_normalize_rejects_ftp():
    with pytest.raises(ValidationError):
        normalize_url("ftp://example.com/file")


def test_normalize_rejects_credentials():
    with pytest.raises(ValidationError):
        normalize_url("https://user:pass@example.com/")


def test_normalize_rejects_blank():
    with pytest.raises(ValidationError):
        normalize_url("   ")


def test_domain_of():
    assert domain_of("https://www.example.com/a") == "example.com"
    assert domain_of("https://sub.example.co.uk/a") == "example.co.uk"
