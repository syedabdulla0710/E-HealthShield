"""
AES-256-GCM Encryption / Decryption
====================================
Provides authenticated encryption for EHR files.

* encrypt_file(plaintext, key)  →  {ciphertext, nonce, tag}
* decrypt_file(ciphertext, key, nonce, tag)  →  plaintext bytes

The 32-byte key is the Kyber shared-secret (used directly).
GCM mode gives us confidentiality + integrity in a single pass.
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# AES-256 requires a 32-byte key
_KEY_LENGTH = 32
# GCM standard nonce size — 96 bits (12 bytes)
_NONCE_LENGTH = 12


def encrypt_file(plaintext: bytes, key: bytes) -> dict:
    """
    Encrypt file bytes using AES-256-GCM.

    Args:
        plaintext: Raw file bytes to encrypt.
        key:       32-byte symmetric key (Kyber shared secret).

    Returns:
        dict with keys:
            - "ciphertext" (bytes): The encrypted data.
            - "nonce"      (bytes): 12-byte nonce used for this encryption.
            - "tag"        (bytes): 16-byte GCM authentication tag.

    Raises:
        ValueError: If key length is not 32 bytes.
    """
    if len(key) != _KEY_LENGTH:
        raise ValueError(
            f"AES-256 requires a {_KEY_LENGTH}-byte key, got {len(key)} bytes."
        )

    nonce = os.urandom(_NONCE_LENGTH)
    aesgcm = AESGCM(key)

    # AESGCM.encrypt appends the 16-byte tag to the ciphertext
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # Separate ciphertext and tag for explicit storage
    tag = ct_with_tag[-16:]
    ciphertext = ct_with_tag[:-16]

    return {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "tag": tag,
    }


def decrypt_file(
    ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes
) -> bytes:
    """
    Decrypt file bytes using AES-256-GCM.

    Args:
        ciphertext: Encrypted file bytes (without tag).
        key:        32-byte symmetric key (same Kyber shared secret).
        nonce:      12-byte nonce that was used during encryption.
        tag:        16-byte GCM authentication tag.

    Returns:
        The original plaintext file bytes.

    Raises:
        ValueError: If key length is not 32 bytes.
        cryptography.exceptions.InvalidTag: If authentication fails
                                            (data tampered or wrong key).
    """
    if len(key) != _KEY_LENGTH:
        raise ValueError(
            f"AES-256 requires a {_KEY_LENGTH}-byte key, got {len(key)} bytes."
        )

    aesgcm = AESGCM(key)

    # Re-append tag to ciphertext (AESGCM.decrypt expects them concatenated)
    ct_with_tag = ciphertext + tag

    plaintext = aesgcm.decrypt(nonce, ct_with_tag, associated_data=None)
    return plaintext
