"""
CRYSTALS-Kyber (ML-KEM) Key Encapsulation
==========================================
Provides post-quantum key exchange for EHR encryption.

* generate_keypair()            ->  (public_key, secret_key)
* encapsulate(public_key)       ->  (kyber_ciphertext, shared_secret)
* decapsulate(ciphertext, sk)   ->  shared_secret

Uses kyber-py (ML-KEM-768 -- NIST security level 3).
The 32-byte shared_secret is used DIRECTLY as the AES-256 key.
"""

from kyber_py.ml_kem import ML_KEM_768


def generate_keypair() -> tuple[bytes, bytes]:
    """
    Generate a persistent Kyber-768 keypair for a user.

    This is called **once** during user registration.
    The public key is shared; the secret key must be stored securely.

    Returns:
        (public_key, secret_key) -- both as raw bytes.
        public_key (encapsulation key): 1184 bytes
        secret_key (decapsulation key): 2400 bytes
    """
    public_key, secret_key = ML_KEM_768.keygen()
    return (public_key, secret_key)


def encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
    """
    Encapsulate: create a shared secret using the receiver's public key.

    Called by the **uploader** (doctor) to encrypt a file for a patient.

    Args:
        public_key: The patient's Kyber public key (1184 bytes).

    Returns:
        (kyber_ciphertext, shared_secret)
        - kyber_ciphertext (1088 bytes): Must be stored alongside the
          encrypted file so the patient can later decapsulate.
        - shared_secret (32 bytes): Used directly as the AES-256 key.
    """
    # kyber-py returns (shared_secret, ciphertext) -- swap for our API
    shared_secret, kyber_ciphertext = ML_KEM_768.encaps(public_key)
    return (kyber_ciphertext, shared_secret)


def decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
    """
    Decapsulate: recover the shared secret using the receiver's secret key.

    Called by the **patient** (or backend on their behalf) to decrypt.

    Args:
        ciphertext:  The Kyber ciphertext stored during upload (1088 bytes).
        secret_key:  The patient's Kyber secret key (2400 bytes).

    Returns:
        shared_secret -- the same 32-byte key that was produced by encapsulate.
    """
    # kyber-py API: decaps(decapsulation_key, ciphertext)
    shared_secret = ML_KEM_768.decaps(secret_key, ciphertext)
    return shared_secret
