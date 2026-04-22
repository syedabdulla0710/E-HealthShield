"""
E-HealthShield — Crypto Module
================================
Quantum-secure encryption engine for Electronic Health Records.

Exports:
    AES:   encrypt_file, decrypt_file
    Kyber: generate_keypair, encapsulate, decapsulate
    SSE:   generate_sse_key, extract_keywords, generate_tags,
           generate_trapdoor, match_trapdoor
    Utils: compute_file_hash, generate_random_bytes
"""

from crypto.aes_handler import encrypt_file, decrypt_file
from crypto.kyber_handler import generate_keypair, encapsulate, decapsulate
from crypto.sse_handler import (
    generate_sse_key,
    extract_keywords,
    generate_tags,
    generate_trapdoor,
    match_trapdoor,
)
from crypto.utils import compute_file_hash, generate_random_bytes

__all__ = [
    # AES
    "encrypt_file",
    "decrypt_file",
    # Kyber
    "generate_keypair",
    "encapsulate",
    "decapsulate",
    # SSE
    "generate_sse_key",
    "extract_keywords",
    "generate_tags",
    "generate_trapdoor",
    "match_trapdoor",
    # Utils
    "compute_file_hash",
    "generate_random_bytes",
]
