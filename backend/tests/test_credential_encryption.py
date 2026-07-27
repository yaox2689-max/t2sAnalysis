"""Tests for credential_encryption — encrypt/decrypt round-trip."""


from app.services.credential_encryption import decrypt_password, encrypt_password


class TestEncryptDecrypt:
    def test_round_trip(self):
        """Encrypt then decrypt returns the original password."""
        original = "my_secret_password_123"
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_different_passwords_different_ciphertext(self):
        """Different passwords produce different ciphertext."""
        enc1 = encrypt_password("password_a")
        enc2 = encrypt_password("password_b")
        assert enc1 != enc2

    def test_same_password_produces_valid_ciphertext(self):
        """Same password always produces valid Fernet ciphertext.

        Fernet includes a timestamp, so two encryptions of the same
        plaintext produce different tokens. Both should decrypt correctly.
        """
        enc1 = encrypt_password("password_a")
        enc2 = encrypt_password("password_a")
        assert enc1 != enc2
        assert decrypt_password(enc1) == "password_a"
        assert decrypt_password(enc2) == "password_a"

    def test_empty_string(self):
        """Empty password can be encrypted and decrypted."""
        encrypted = encrypt_password("")
        decrypted = decrypt_password(encrypted)
        assert decrypted == ""

    def test_unicode_password(self):
        """Unicode (Chinese) password works correctly."""
        original = "密码_测试_🔑"
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original

    def test_long_password(self):
        """Long password round-trips correctly."""
        original = "x" * 1000
        encrypted = encrypt_password(original)
        decrypted = decrypt_password(encrypted)
        assert decrypted == original
