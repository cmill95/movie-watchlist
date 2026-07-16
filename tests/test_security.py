"""Unit tests for password hashing."""

from app.security import hash_password, verify_password


def test_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password("correct horse battery", hashed) is True


def test_verify_rejects_wrong_password():
    hashed = hash_password("correct horse battery")
    assert verify_password("wrong", hashed) is False


def test_hash_is_salted_so_two_hashes_differ():
    assert hash_password("same-password") != hash_password("same-password")
