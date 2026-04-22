# 🔐 Crypto Module — E-HealthShield

The encryption engine that powers E-HealthShield's secure EHR system. This module provides **AES-256-GCM encryption**, **post-quantum key exchange (CRYSTALS-Kyber)**, **searchable symmetric encryption (SSE)**, and **hashing utilities**.

> ⚠️ This module is imported by the Backend (`/backend`). It does **not** run standalone — it's a Python package.

---

## 📁 File Structure

```
crypto/
├── __init__.py          # Package exports (all public functions)
├── aes_handler.py       # AES-256-GCM encrypt / decrypt
├── kyber_handler.py     # CRYSTALS-Kyber ML-KEM-768 key encapsulation
├── sse_handler.py       # Symmetric Searchable Encryption (HMAC-SHA256)
├── utils.py             # SHA-256 hashing & random byte generation
├── requirements.txt     # Python dependencies
├── test_crypto.py       # Unit tests (34 tests)
└── README.md            # ← You are here
```

---

## 🧰 Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)

---

## ⚙️ Setup

### 1. Clone & switch to the crypto branch

```bash
git clone https://github.com/syedabdulla0710/E-HealthShield.git
cd E-HealthShield
git checkout crypto-setup
```

### 2. Install dependencies

```bash
pip install -r crypto/requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `cryptography` (≥42.0) | AES-256-GCM encryption |
| `kyber-py` (≥0.2) | CRYSTALS-Kyber / ML-KEM-768 post-quantum KEM |
| `PyPDF2` (≥3.0) | PDF text extraction for SSE keyword extraction |
| `pytest` (≥8.0) | Unit test framework |

---

## ✅ Running Tests

Run all 34 tests from the **project root** (`E-HealthShield/`):

```bash
python -m pytest crypto/test_crypto.py -v
```

Expected output:

```
crypto/test_crypto.py::TestAES::test_roundtrip_basic PASSED
crypto/test_crypto.py::TestAES::test_roundtrip_large_file PASSED
crypto/test_crypto.py::TestAES::test_roundtrip_empty PASSED
crypto/test_crypto.py::TestAES::test_wrong_key_fails PASSED
crypto/test_crypto.py::TestAES::test_tampered_ciphertext_fails PASSED
crypto/test_crypto.py::TestAES::test_tampered_tag_fails PASSED
crypto/test_crypto.py::TestAES::test_invalid_key_length PASSED
crypto/test_crypto.py::TestAES::test_output_structure PASSED
crypto/test_crypto.py::TestAES::test_different_nonces PASSED
crypto/test_crypto.py::TestKyber::test_keygen_returns_bytes PASSED
crypto/test_crypto.py::TestKyber::test_encapsulate_decapsulate_roundtrip PASSED
crypto/test_crypto.py::TestKyber::test_shared_secret_length PASSED
crypto/test_crypto.py::TestKyber::test_different_keypairs_different_secrets PASSED
crypto/test_crypto.py::TestKyber::test_wrong_secret_key_fails PASSED
crypto/test_crypto.py::TestKyberAESPipeline::test_full_pipeline PASSED
crypto/test_crypto.py::TestSSE::test_sse_key_length PASSED
...
============================= 34 passed ==============================
```

---

## 📐 Module Details

### 1. `aes_handler.py` — AES-256-GCM Encryption

Provides authenticated encryption using AES-256 in GCM mode. GCM gives both **confidentiality** and **integrity** in a single pass.

#### Functions

```python
encrypt_file(plaintext: bytes, key: bytes) -> dict
```
- **Input**: Raw file bytes + 32-byte key (Kyber shared secret)
- **Output**: `{"ciphertext": bytes, "nonce": bytes (12B), "tag": bytes (16B)}`
- Generates a unique random nonce per encryption

```python
decrypt_file(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes
```
- **Input**: Encrypted data + key + nonce + tag
- **Output**: Original plaintext bytes
- Raises `InvalidTag` if data has been tampered with or wrong key is used

---

### 2. `kyber_handler.py` — CRYSTALS-Kyber (ML-KEM-768)

Post-quantum key encapsulation mechanism. The shared secret produced by Kyber is used **directly** as the AES-256 key (no extra wrapping).

#### Functions

```python
generate_keypair() -> tuple[bytes, bytes]
```
- Called **once** during user registration
- Returns `(public_key [1184B], secret_key [2400B])`

```python
encapsulate(public_key: bytes) -> tuple[bytes, bytes]
```
- Called by the **doctor** (uploader) using the patient's public key
- Returns `(kyber_ciphertext [1088B], shared_secret [32B])`
- The shared_secret **is** the AES key

```python
decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes
```
- Called by the **patient** to recover the shared secret
- Returns the same 32-byte shared_secret

---

### 3. `sse_handler.py` — Symmetric Searchable Encryption

Enables keyword search over encrypted files **without decrypting** them. Uses HMAC-SHA256 for tag and trapdoor generation.

#### Functions

```python
generate_sse_key() -> bytes
```
- Generates a 32-byte master SSE key (stored in backend `.env`)

```python
extract_keywords(file_bytes: bytes, filename: str) -> list[str]
```
- Extracts keywords from `.txt`, `.csv`, `.json`, `.xml`, `.html`, `.pdf` files
- Removes stop-words, short tokens, duplicates
- Always includes keywords from the filename

```python
generate_tags(sse_key: bytes, keywords: list[str]) -> list[str]
```
- Generates `HMAC-SHA256(sse_key, keyword)` for each keyword
- Returns hex-encoded tag strings (stored alongside encrypted files)

```python
generate_trapdoor(sse_key: bytes, keyword: str) -> str
```
- Generates a search trapdoor (same as a tag) for a single keyword
- Case-insensitive

```python
match_trapdoor(trapdoor: str, tags: list[str]) -> bool
```
- Checks if a trapdoor matches any stored tag
- Uses **constant-time comparison** (`hmac.compare_digest`) to prevent timing attacks

---

### 4. `utils.py` — Hashing & Random Bytes

```python
compute_file_hash(data: bytes) -> str
```
- SHA-256 hash of file bytes (stored on blockchain for integrity verification)
- Returns 64-character hex string

```python
generate_random_bytes(n: int) -> bytes
```
- Cryptographically secure random bytes via `os.urandom`

---

## 🔄 How It All Fits Together

### Upload Flow (Doctor encrypts for Patient)

```
1. Doctor uploads a file
2. extract_keywords(file)           → ["diabetes", "insulin", ...]
3. generate_tags(sse_key, keywords) → ["a1b2c3...", "d4e5f6..."]
4. generate_keypair()               → (patient_pk, patient_sk)  [done at registration]
5. encapsulate(patient_pk)          → (kyber_ct, shared_secret)
6. encrypt_file(file, shared_secret)→ {ciphertext, nonce, tag}
7. compute_file_hash(file)          → "sha256hex..."
8. Store: ciphertext + nonce + tag + kyber_ct + sse_tags + hash → MongoDB
9. Store: hash → Blockchain
```

### Decrypt Flow (Patient recovers file)

```
1. Patient requests file
2. Fetch kyber_ct from MongoDB
3. decapsulate(kyber_ct, patient_sk) → shared_secret
4. decrypt_file(ciphertext, shared_secret, nonce, tag) → original file
5. Verify: compute_file_hash(decrypted) == blockchain hash
```

### Search Flow (Find files by keyword)

```
1. User searches for "diabetes"
2. generate_trapdoor(sse_key, "diabetes") → "a1b2c3..."
3. For each file: match_trapdoor(trapdoor, file.sse_tags)
4. Return matching files
```

---

## 🧪 Test Coverage (34 Tests)

| Test Class | Count | What's Tested |
|------------|-------|---------------|
| `TestAES` | 9 | Round-trips (basic, 1MB, empty), wrong key, tampered data, tampered tag, invalid key length, output structure, nonce uniqueness |
| `TestKyber` | 5 | Keygen types, encap/decap round-trip, 32-byte secret, different keypairs, wrong secret key |
| `TestKyberAESPipeline` | 1 | Full end-to-end: Kyber → AES encrypt → Kyber → AES decrypt |
| `TestSSE` | 12 | Keyword extraction (.txt, .csv, empty), tag generation, trapdoor matching, case-insensitivity, wrong-key rejection |
| `TestUtils` | 7 | Hash determinism, hex format, different data, empty data, random byte length, randomness, invalid length |

---

## 🔑 Key Design Decisions

1. **Kyber shared secret = AES key** — No separate key wrapping. The 32-byte shared secret from ML-KEM-768 is used directly as the AES-256 key.
2. **Single global SSE key** — One HMAC key for all tags/trapdoors (prototype simplification). Production would use per-user keys.
3. **Constant-time tag matching** — `hmac.compare_digest` prevents timing side-channel attacks.
4. **Graceful PDF fallback** — If PyPDF2 is not installed, keyword extraction still works using the filename.
