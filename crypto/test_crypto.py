"""
E-HealthShield — Crypto Module Unit Tests
==========================================
Run:  python -m pytest crypto/test_crypto.py -v
From: E-HealthShield/  (project root)
"""

import os
import pytest

# ---------------------------------------------------------------------------
# AES-256-GCM Tests
# ---------------------------------------------------------------------------
from crypto.aes_handler import encrypt_file, decrypt_file


class TestAES:
    """AES-256-GCM encrypt / decrypt round-trip tests."""

    def test_roundtrip_basic(self):
        """Encrypt then decrypt should return the original plaintext."""
        key = os.urandom(32)
        plaintext = b"Hello, E-HealthShield!"

        result = encrypt_file(plaintext, key)
        decrypted = decrypt_file(
            result["ciphertext"], key, result["nonce"], result["tag"]
        )
        assert decrypted == plaintext

    def test_roundtrip_large_file(self):
        """Should handle a 1 MB payload without issues."""
        key = os.urandom(32)
        plaintext = os.urandom(1_000_000)  # 1 MB of random data

        result = encrypt_file(plaintext, key)
        decrypted = decrypt_file(
            result["ciphertext"], key, result["nonce"], result["tag"]
        )
        assert decrypted == plaintext

    def test_roundtrip_empty(self):
        """Empty plaintext should encrypt and decrypt cleanly."""
        key = os.urandom(32)
        plaintext = b""

        result = encrypt_file(plaintext, key)
        decrypted = decrypt_file(
            result["ciphertext"], key, result["nonce"], result["tag"]
        )
        assert decrypted == plaintext

    def test_wrong_key_fails(self):
        """Decryption with a different key must raise an error."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Sensitive medical data"

        result = encrypt_file(plaintext, key1)
        with pytest.raises(Exception):
            decrypt_file(result["ciphertext"], key2, result["nonce"], result["tag"])

    def test_tampered_ciphertext_fails(self):
        """Modifying ciphertext should cause authentication failure."""
        key = os.urandom(32)
        plaintext = b"Patient record #12345"

        result = encrypt_file(plaintext, key)
        tampered = bytearray(result["ciphertext"])
        if len(tampered) > 0:
            tampered[0] ^= 0xFF  # Flip bits
        with pytest.raises(Exception):
            decrypt_file(bytes(tampered), key, result["nonce"], result["tag"])

    def test_tampered_tag_fails(self):
        """Modifying the tag should cause authentication failure."""
        key = os.urandom(32)
        plaintext = b"Lab results"

        result = encrypt_file(plaintext, key)
        tampered_tag = bytearray(result["tag"])
        tampered_tag[0] ^= 0xFF
        with pytest.raises(Exception):
            decrypt_file(
                result["ciphertext"], key, result["nonce"], bytes(tampered_tag)
            )

    def test_invalid_key_length(self):
        """Keys that are not 32 bytes should raise ValueError."""
        with pytest.raises(ValueError):
            encrypt_file(b"data", b"short_key")
        with pytest.raises(ValueError):
            decrypt_file(b"ct", b"short_key", b"nonce", b"tag")

    def test_output_structure(self):
        """encrypt_file should return dict with ciphertext, nonce, tag."""
        key = os.urandom(32)
        result = encrypt_file(b"test", key)

        assert isinstance(result, dict)
        assert "ciphertext" in result
        assert "nonce" in result
        assert "tag" in result
        assert len(result["nonce"]) == 12
        assert len(result["tag"]) == 16

    def test_different_nonces(self):
        """Two encryptions of the same data should use different nonces."""
        key = os.urandom(32)
        plaintext = b"Same data"

        r1 = encrypt_file(plaintext, key)
        r2 = encrypt_file(plaintext, key)
        assert r1["nonce"] != r2["nonce"]


# ---------------------------------------------------------------------------
# Kyber (ML-KEM-768) Tests
# ---------------------------------------------------------------------------
from crypto.kyber_handler import generate_keypair, encapsulate, decapsulate


class TestKyber:
    """CRYSTALS-Kyber key encapsulation tests."""

    def test_keygen_returns_bytes(self):
        """generate_keypair should return a tuple of two byte strings."""
        pk, sk = generate_keypair()
        assert isinstance(pk, bytes)
        assert isinstance(sk, bytes)
        assert len(pk) > 0
        assert len(sk) > 0

    def test_encapsulate_decapsulate_roundtrip(self):
        """Encapsulate + decapsulate should produce the same shared secret."""
        pk, sk = generate_keypair()
        ct, shared_secret_enc = encapsulate(pk)
        shared_secret_dec = decapsulate(ct, sk)

        assert shared_secret_enc == shared_secret_dec

    def test_shared_secret_length(self):
        """Shared secret should be 32 bytes (usable as AES-256 key)."""
        pk, sk = generate_keypair()
        ct, shared_secret = encapsulate(pk)
        assert len(shared_secret) == 32

    def test_different_keypairs_different_secrets(self):
        """Two different keypairs should produce different shared secrets."""
        pk1, sk1 = generate_keypair()
        pk2, sk2 = generate_keypair()

        ct1, ss1 = encapsulate(pk1)
        ct2, ss2 = encapsulate(pk2)

        # Different public keys -> (almost certainly) different secrets
        assert ss1 != ss2

    def test_wrong_secret_key_fails(self):
        """Decapsulating with a wrong secret key should yield a different secret."""
        pk1, sk1 = generate_keypair()
        _, sk2 = generate_keypair()

        ct, shared_secret_enc = encapsulate(pk1)
        shared_secret_wrong = decapsulate(ct, sk2)

        # Kyber has implicit reject -- wrong sk produces a different secret
        assert shared_secret_enc != shared_secret_wrong


# ---------------------------------------------------------------------------
# Full Pipeline: Kyber + AES Round-Trip
# ---------------------------------------------------------------------------
class TestKyberAESPipeline:
    """End-to-end: Kyber key exchange → AES encrypt → AES decrypt."""

    def test_full_pipeline(self):
        """Simulate the complete upload-then-decrypt flow."""
        # 1. Patient registers — generate keypair
        pk, sk = generate_keypair()

        # 2. Doctor uploads — encapsulate to get shared secret
        kyber_ct, shared_secret = encapsulate(pk)

        # 3. Doctor encrypts the file with the shared secret
        plaintext = b"Patient: John Doe | Diagnosis: Healthy"
        aes_result = encrypt_file(plaintext, shared_secret)

        # 4. Patient decrypts — decapsulate to recover shared secret
        recovered_secret = decapsulate(kyber_ct, sk)
        assert recovered_secret == shared_secret

        # 5. Patient decrypts the file
        decrypted = decrypt_file(
            aes_result["ciphertext"],
            recovered_secret,
            aes_result["nonce"],
            aes_result["tag"],
        )
        assert decrypted == plaintext


# ---------------------------------------------------------------------------
# SSE (Searchable Symmetric Encryption) Tests
# ---------------------------------------------------------------------------
from crypto.sse_handler import (
    generate_sse_key,
    extract_keywords,
    generate_tags,
    generate_trapdoor,
    match_trapdoor,
)


class TestSSE:
    """Symmetric Searchable Encryption tests."""

    def test_sse_key_length(self):
        """SSE key should be 32 bytes."""
        key = generate_sse_key()
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_extract_keywords_txt(self):
        """Should extract meaningful keywords from text content."""
        content = b"Patient has diabetes and requires insulin treatment"
        keywords = extract_keywords(content, "report.txt")

        assert "diabetes" in keywords
        assert "insulin" in keywords
        assert "treatment" in keywords
        assert "report" in keywords  # from filename
        # Stop-words should be excluded
        assert "and" not in keywords
        assert "has" not in keywords

    def test_extract_keywords_csv(self):
        """Should extract keywords from CSV content."""
        content = b"name,diagnosis,medication\nJohn,diabetes,metformin"
        keywords = extract_keywords(content, "patients.csv")

        assert "diabetes" in keywords
        assert "metformin" in keywords
        assert "patients" in keywords  # from filename

    def test_extract_keywords_empty(self):
        """Empty content should still return filename keywords."""
        keywords = extract_keywords(b"", "blood_test.txt")
        assert "blood" in keywords
        assert "test" in keywords

    def test_generate_tags_deterministic(self):
        """Same key + keywords should produce same tags."""
        key = b"0" * 32
        keywords = ["diabetes", "insulin"]

        tags1 = generate_tags(key, keywords)
        tags2 = generate_tags(key, keywords)

        assert tags1 == tags2

    def test_generate_tags_count(self):
        """Should generate one tag per keyword."""
        key = generate_sse_key()
        keywords = ["diabetes", "insulin", "glucose"]
        tags = generate_tags(key, keywords)

        assert len(tags) == 3

    def test_tags_are_hex_strings(self):
        """Tags should be hex-encoded strings."""
        key = generate_sse_key()
        tags = generate_tags(key, ["diabetes"])

        assert len(tags) == 1
        assert isinstance(tags[0], str)
        # SHA-256 hex digest is 64 characters
        assert len(tags[0]) == 64

    def test_trapdoor_matches_tag(self):
        """A trapdoor for a keyword should match its tag."""
        key = generate_sse_key()
        keywords = ["diabetes", "insulin", "glucose"]
        tags = generate_tags(key, keywords)

        trapdoor = generate_trapdoor(key, "diabetes")
        assert match_trapdoor(trapdoor, tags) is True

    def test_trapdoor_no_match(self):
        """A trapdoor for a non-existent keyword should not match."""
        key = generate_sse_key()
        keywords = ["diabetes", "insulin"]
        tags = generate_tags(key, keywords)

        trapdoor = generate_trapdoor(key, "cancer")
        assert match_trapdoor(trapdoor, tags) is False

    def test_trapdoor_case_insensitive(self):
        """Trapdoor generation should be case-insensitive."""
        key = generate_sse_key()
        tags = generate_tags(key, ["diabetes"])

        trapdoor_lower = generate_trapdoor(key, "diabetes")
        trapdoor_upper = generate_trapdoor(key, "DIABETES")
        trapdoor_mixed = generate_trapdoor(key, "Diabetes")

        assert trapdoor_lower == trapdoor_upper == trapdoor_mixed
        assert match_trapdoor(trapdoor_upper, tags) is True

    def test_different_keys_different_tags(self):
        """Different SSE keys should produce different tags."""
        key1 = generate_sse_key()
        key2 = generate_sse_key()

        tags1 = generate_tags(key1, ["diabetes"])
        tags2 = generate_tags(key2, ["diabetes"])

        assert tags1 != tags2

    def test_wrong_key_trapdoor_no_match(self):
        """Trapdoor generated with wrong key should not match tags."""
        key1 = generate_sse_key()
        key2 = generate_sse_key()

        tags = generate_tags(key1, ["diabetes"])
        trapdoor = generate_trapdoor(key2, "diabetes")

        assert match_trapdoor(trapdoor, tags) is False


# ---------------------------------------------------------------------------
# Utils Tests
# ---------------------------------------------------------------------------
from crypto.utils import compute_file_hash, generate_random_bytes


class TestUtils:
    """Utility function tests."""

    def test_file_hash_deterministic(self):
        """Same data should always produce the same hash."""
        data = b"Patient record data"
        h1 = compute_file_hash(data)
        h2 = compute_file_hash(data)
        assert h1 == h2

    def test_file_hash_is_hex(self):
        """Hash should be a 64-character hex string."""
        h = compute_file_hash(b"test")
        assert isinstance(h, str)
        assert len(h) == 64
        int(h, 16)  # Should not raise

    def test_file_hash_different_data(self):
        """Different data should produce different hashes."""
        h1 = compute_file_hash(b"data1")
        h2 = compute_file_hash(b"data2")
        assert h1 != h2

    def test_file_hash_empty(self):
        """Empty bytes should still produce a valid hash."""
        h = compute_file_hash(b"")
        assert len(h) == 64

    def test_random_bytes_length(self):
        """Should generate the requested number of bytes."""
        for n in [1, 16, 32, 64, 256]:
            rb = generate_random_bytes(n)
            assert len(rb) == n

    def test_random_bytes_are_random(self):
        """Two calls should (almost certainly) produce different results."""
        r1 = generate_random_bytes(32)
        r2 = generate_random_bytes(32)
        assert r1 != r2

    def test_random_bytes_invalid_length(self):
        """Zero or negative lengths should raise ValueError."""
        with pytest.raises(ValueError):
            generate_random_bytes(0)
        with pytest.raises(ValueError):
            generate_random_bytes(-1)
