"""
Crypto Utilities
================
Shared helpers used across the crypto module.

* compute_file_hash(data)       ->  SHA-256 hex string
* generate_random_bytes(n)      ->  n random bytes
"""

import hashlib
import os


def compute_file_hash(data: bytes) -> str:
    """
    Compute the SHA-256 hash of raw file bytes.

    This hash is stored on the blockchain for integrity verification.
    During decryption the hash of the decrypted file is compared against
    the on-chain hash to detect tampering.

    Args:
        data: Raw (plaintext) file bytes.

    Returns:
        Lowercase hex-encoded SHA-256 digest (64 characters).
    """
    return hashlib.sha256(data).hexdigest()


def generate_random_bytes(n: int) -> bytes:
    """
    Generate *n* cryptographically-secure random bytes.

    Thin wrapper around ``os.urandom`` for consistency / testability.

    Args:
        n: Number of bytes to generate (must be > 0).

    Returns:
        Bytes object of length *n*.

    Raises:
        ValueError: If n <= 0.
    """
    if n <= 0:
        raise ValueError(f"Byte count must be positive, got {n}.")
    return os.urandom(n)
