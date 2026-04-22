# 🛡️ E-HealthShield — Implementation Plan

**A Quantum-Secure, Blockchain-Auditable Framework for Electronic Health Records (EHRs)**

> This document is the complete implementation guide. Every team member and AI agent
> should read their relevant section before writing any code.

---

## 📌 Table of Contents

1. [Architecture Diagram](#-architecture-diagram)
2. [Tech Stack](#-tech-stack)
3. [Team Roles & Responsibilities](#-team-roles--responsibilities)
4. [Project Structure](#-project-structure)
5. [Data Flow — Upload](#-data-flow--upload)
6. [Data Flow — Search & Decrypt](#-data-flow--search--decrypt)
7. [Module Details](#-module-details)
8. [Database Schemas](#-database-schemas)
9. [API Reference](#-api-reference)
10. [Smart Contract Interface](#-smart-contract-interface)
11. [Key Design Decisions](#-key-design-decisions)
12. [Setup & Running](#-setup--running)
13. [Security Notes](#-security-notes)
14. [Future Scope](#-future-scope)

---

## ✅ Key Improvements (Final Revision)

| #  | Improvement                | Description                                     |
| -- | -------------------------- | ----------------------------------------------- |
| 1  | Persistent Kyber keypairs  | Each user has a fixed keypair (not per upload)  |
| 2  | Simplified key usage       | Kyber shared secret used directly as AES key    |
| 3  | Auto keyword extraction    | Extract keywords from file automatically        |
| 4  | MongoDB optimization       | Direct storage for demo, GridFS/IPFS for future |
| 5  | Blockchain scope reduction | Only hash + ACL + audit logs                    |
| 6  | Modular backend design     | Upload, Search, Access services separated       |
| 7  | Role-based access          | Doctor (upload/manage) & Patient (view)         |
| 8  | Security clarification     | Prototype limitations clearly mentioned         |
| 9  | Error handling             | Proper HTTP errors for all cases                |
| 10 | Logging system             | Track upload, search, and access events         |
| 11 | SSE key management         | Single backend-managed SSE key                  |
| 12 | File size control          | Limit file size to 10 MB for stability          |

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Ethers.js)         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Patient View  │  │ Doctor View  │  │ MetaMask Auth │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (HTTPS)
┌────────────────────────▼────────────────────────────────┐
│                    BACKEND (FastAPI)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Upload   │ │ Search   │ │ Access   │ │ Decrypt   │  │
│  │ Service  │ │ Service  │ │ Control  │ │ Service   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │           CRYPTO MODULE (imported)               │   │
│  │    AES-256  │  Kyber ML-KEM  │  SSE (HMAC)      │   │
│  └──────────────────────────────────────────────────┘   │
└───────┬─────────────────────────────────┬───────────────┘
        │                                 │
┌───────▼───────────┐           ┌─────────▼──────────────┐
│   MongoDB         │           │   Ethereum Blockchain  │
│ ┌───────────────┐ │           │ ┌────────────────────┐ │
│ │ users         │ │           │ │ EHRAccessControl   │ │
│ │ encrypted_    │ │           │ │ - File hashes      │ │
│ │   files       │ │           │ │ - ACL per file     │ │
│ └───────────────┘ │           │ │ - Audit events     │ │
└───────────────────┘           │ └────────────────────┘ │
                                └────────────────────────┘
```

---

## 🧰 Tech Stack

| Layer        | Technology                 | Version     |
| ------------ | -------------------------- | ----------- |
| Frontend     | React + Vite               | React 18+   |
| Wallet Auth  | Ethers.js + MetaMask       | Ethers v6   |
| Backend API  | FastAPI (Python)           | 0.111+      |
| Database     | MongoDB + Motor (async)    | Motor 3.4+  |
| Encryption   | AES-256-GCM (`cryptography` lib) | 42+   |
| Post-Quantum | CRYSTALS-Kyber (`kyber-py`) | Latest     |
| SSE          | HMAC-SHA256 (stdlib)       | Python 3.10+|
| Blockchain   | Solidity + Hardhat         | Solidity 0.8.20 |
| Testing      | Pytest / Hardhat / Vitest  | Latest      |

---

## 👥 Team Roles & Responsibilities

### Member 1 — 🔐 Crypto Developer (`/crypto`)

**Branch:** `crypto-setup`

**You build the encryption engine. Your code is imported by the Backend.**

| Task | Description |
| ---- | ----------- |
| `aes_handler.py` | AES-256-GCM encrypt/decrypt functions |
| `kyber_handler.py` | Kyber keypair generation, encapsulate, decapsulate |
| `sse_handler.py` | SSE key gen, keyword extraction, tag generation, trapdoor matching |
| `utils.py` | SHA-256 file hashing, random byte generation |
| Unit tests | Test all encrypt/decrypt roundtrips and SSE matching |

**Key rule:** Kyber shared secret is used **directly** as the AES key (no separate wrapping).

---

### Member 2 — ⚙️ Backend Developer (`/backend`)

**Branch:** `backend-setup`

**You build the FastAPI server. You import `/crypto` and connect to MongoDB + Blockchain.**

| Task | Description |
| ---- | ----------- |
| `main.py` | FastAPI app with CORS, lifespan, routes |
| `config.py` | Environment variables (.env) |
| `database.py` | MongoDB async connection (Motor) |
| `blockchain_client.py` | Web3.py client for smart contract |
| `logger.py` | Logging for upload/search/access events |
| `routes/auth.py` | User registration + Kyber keypair storage |
| `routes/upload.py` | File upload → encrypt → store → blockchain hash |
| `routes/search.py` | Keyword → trapdoor → SSE tag matching |
| `routes/access.py` | Grant/revoke access via smart contract |
| `routes/decrypt.py` | Verify access → decrypt → return file |

**Key rules:**
- File size limit: **10 MB** max
- Proper error handling on every route (404, 403, 400, 500)
- Log every upload, search, and access event

---

### Member 3 — ⛓️ Blockchain Developer (`/blockchain`)

**Branch:** `blockchain-setup`

**You build the Solidity smart contract and deployment scripts.**

| Task | Description |
| ---- | ----------- |
| `EHRAccessControl.sol` | Smart contract with file hash storage, ACL, audit events |
| `deploy.js` | Hardhat deployment script |
| `hardhat.config.js` | Network config (local + Sepolia) |
| Tests | Test all contract functions |

**Key rules:**
- Blockchain stores **ONLY**: file hashes, access lists, audit logs
- **NEVER** store files or encryption keys on-chain
- Only the file **owner** can grant/revoke access
- Emit events for every action (audit trail)

---

### Member 4 — 👨‍🎨 Frontend Developer (`/frontend`)

**Branch:** `frontend-setup`

**You build the React UI with MetaMask wallet integration.**

| Task | Description |
| ---- | ----------- |
| `WalletConnect.jsx` | MetaMask login + user registration |
| `Dashboard.jsx` | Role-based view (Doctor vs Patient) |
| `UploadForm.jsx` | File upload with keyword preview |
| `SearchPanel.jsx` | Keyword search input |
| `FileList.jsx` | Display search results |
| `DecryptViewer.jsx` | Decrypt and download file |
| `AccessControl.jsx` | Grant/revoke access UI |
| `services/api.js` | Axios calls to backend |
| `services/blockchain.js` | Ethers.js contract interaction |

**Key rules:**
- All API calls go to backend (`http://localhost:8000/api/...`)
- MetaMask provides the wallet address (no passwords)
- Role-based UI: Doctor sees upload + manage; Patient sees search + view

---

## 📁 Project Structure

```
E-HealthShield/
│
├── crypto/                          # 🔐 Member 1
│   ├── __init__.py                  # Module exports
│   ├── aes_handler.py               # AES-256-GCM encrypt/decrypt
│   ├── kyber_handler.py             # Kyber keygen/encap/decap
│   ├── sse_handler.py               # SSE tags + keyword extraction
│   ├── utils.py                     # Hashing utilities
│   ├── requirements.txt             # cryptography, kyber-py
│   └── test_crypto.py               # Unit tests
│
├── backend/                         # ⚙️ Member 2
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Environment config
│   ├── database.py                  # MongoDB connection
│   ├── blockchain_client.py         # Web3 contract client
│   ├── logger.py                    # Event logging
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                  # POST /api/register
│   │   ├── upload.py                # POST /api/upload
│   │   ├── search.py                # POST /api/search
│   │   ├── access.py                # POST /api/grant-access, /revoke-access
│   │   └── decrypt.py               # POST /api/decrypt/{file_id}
│   ├── .env                         # Environment variables
│   ├── requirements.txt             # fastapi, motor, web3, etc.
│   └── test_api.py                  # API tests
│
├── blockchain/                      # ⛓️ Member 3
│   ├── contracts/
│   │   └── EHRAccessControl.sol     # Solidity smart contract
│   ├── scripts/
│   │   └── deploy.js                # Deployment script
│   ├── test/
│   │   └── EHRAccessControl.test.js # Contract tests
│   ├── hardhat.config.js            # Hardhat config
│   └── package.json                 # Node dependencies
│
├── frontend/                        # 👨‍🎨 Member 4
│   ├── public/
│   ├── src/
│   │   ├── App.jsx                  # Main app + routing
│   │   ├── main.jsx                 # React entry
│   │   ├── index.css                # Global styles
│   │   ├── components/
│   │   │   ├── WalletConnect.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── UploadForm.jsx
│   │   │   ├── SearchPanel.jsx
│   │   │   ├── FileList.jsx
│   │   │   ├── DecryptViewer.jsx
│   │   │   └── AccessControl.jsx
│   │   ├── services/
│   │   │   ├── api.js               # Backend API calls
│   │   │   └── blockchain.js        # Smart contract calls
│   │   └── utils/
│   │       └── constants.js         # Contract address, ABI
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── implementation_plan.md           # ← This file
└── README.md                        # Project overview
```

---

## 📤 Data Flow — Upload

```
Step  Action                          Module         Detail
─────────────────────────────────────────────────────────────────
 1    Doctor uploads EHR file          Frontend       POST /api/upload
 2    Extract keywords from file       Crypto (SSE)   extract_keywords(file_bytes)
 3    Generate SSE tags from keywords  Crypto (SSE)   HMAC(sse_key, keyword) for each
 4    Fetch patient's Kyber public key Backend (DB)   From users collection
 5    Kyber encapsulate                Crypto (Kyber) encapsulate(patient_pk) → (ct, shared_secret)
 6    AES encrypt file                 Crypto (AES)   encrypt(file, shared_secret)
 7    Compute file hash                Crypto (Utils) SHA-256(original_file)
 8    Store hash on blockchain         Blockchain     uploadFile(file_id, hash)
 9    Store encrypted bundle in DB     Backend (DB)   MongoDB insert
10    Log upload event                 Backend        logger.log_upload(...)
```

---

## 🔍 Data Flow — Search & Decrypt

```
SEARCH:
Step  Action                          Module         Detail
─────────────────────────────────────────────────────────────────
 1    User enters search keyword       Frontend       POST /api/search
 2    Generate trapdoor                Crypto (SSE)   HMAC(sse_key, keyword)
 3    Match trapdoor vs SSE tags       Backend (DB)   MongoDB query
 4    Return matching file metadata    Backend        List of file_id, filename, etc.

DECRYPT:
Step  Action                          Module         Detail
─────────────────────────────────────────────────────────────────
 1    User requests file decryption    Frontend       POST /api/decrypt/{file_id}
 2    Check access via smart contract  Blockchain     checkAccess(file_id, wallet)
 3    Verify file hash on blockchain   Blockchain     getFileHash(file_id) == stored hash
 4    Fetch Kyber secret key           Backend (DB)   From users collection (demo)
 5    Kyber decapsulate                Crypto (Kyber) decapsulate(ct, sk) → shared_secret
 6    AES decrypt file                 Crypto (AES)   decrypt(ciphertext, shared_secret)
 7    Return decrypted file            Backend        Streaming file response
 8    Log access event                 Backend        logger.log_access(...)
```

---

## 📐 Module Details

### 🔐 Crypto Module (Member 1)

#### `aes_handler.py`

```python
def encrypt_file(plaintext: bytes, key: bytes) -> dict:
    """
    Encrypt file using AES-256-GCM.
    Args:
        plaintext: Raw file bytes
        key: 32-byte key (Kyber shared secret)
    Returns:
        {"ciphertext": bytes, "nonce": bytes, "tag": bytes}
    """

def decrypt_file(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    """
    Decrypt file using AES-256-GCM.
    Returns: Original file bytes
    """
```

#### `kyber_handler.py`

```python
def generate_keypair() -> tuple[bytes, bytes]:
    """
    Generate persistent Kyber keypair for a user.
    Returns: (public_key, secret_key)
    Called ONCE during user registration.
    """

def encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
    """
    Create shared secret using receiver's public key.
    Returns: (kyber_ciphertext, shared_secret)
    shared_secret IS the AES key (32 bytes).
    """

def decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
    """
    Recover shared secret using own secret key.
    Returns: shared_secret (same 32 bytes)
    """
```

#### `sse_handler.py`

```python
def generate_sse_key() -> bytes:
    """Generate 32-byte SSE key (stored in backend config)."""

def extract_keywords(file_bytes: bytes, filename: str) -> list[str]:
    """
    Auto-extract keywords from file content.
    Supports: .txt, .pdf (basic), .csv
    Returns: List of lowercase keyword strings
    """

def generate_tags(sse_key: bytes, keywords: list[str]) -> list[str]:
    """
    Generate SSE tags: HMAC-SHA256(sse_key, keyword) for each keyword.
    Returns: List of hex-encoded tag strings
    """

def generate_trapdoor(sse_key: bytes, keyword: str) -> str:
    """
    Generate search trapdoor (same as tag generation).
    Returns: Hex-encoded trapdoor string
    """

def match_trapdoor(trapdoor: str, tags: list[str]) -> bool:
    """
    Check if trapdoor matches any tag.
    Uses constant-time comparison (hmac.compare_digest).
    """
```

#### `utils.py`

```python
def compute_file_hash(data: bytes) -> str:
    """Compute SHA-256 hash of file bytes. Returns hex string."""

def generate_random_bytes(n: int) -> bytes:
    """Generate n cryptographically secure random bytes."""
```

---

## 🗄️ Database Schemas

### `users` Collection

```json
{
  "_id": "ObjectId",
  "wallet_address": "0xAbC123...",
  "role": "doctor",
  "kyber_public_key": "<base64 encoded>",
  "kyber_secret_key": "<base64 encoded — demo only>",
  "registered_at": "2026-04-22T06:30:00Z"
}
```

### `encrypted_files` Collection

```json
{
  "_id": "ObjectId",
  "file_id": "uuid-string",
  "filename": "patient_report.pdf",
  "owner_wallet": "0xAbC123...",
  "patient_wallet": "0xDeF456...",
  "encrypted_data": "<base64 AES ciphertext>",
  "aes_nonce": "<base64>",
  "aes_tag": "<base64>",
  "kyber_ciphertext": "<base64>",
  "sse_tags": ["a1b2c3...", "d4e5f6..."],
  "file_hash": "sha256hexstring",
  "file_size": 245000,
  "uploaded_at": "2026-04-22T06:30:00Z"
}
```

---

## 📡 API Reference

**Base URL:** `http://localhost:8000/api`

### `POST /api/register`

Register a new user and generate Kyber keypair.

```
Request Body (JSON):
{
  "wallet_address": "0x...",
  "role": "doctor"              // "doctor" or "patient"
}

Response (200):
{
  "wallet_address": "0x...",
  "role": "doctor",
  "kyber_public_key": "<base64>",
  "message": "User registered successfully"
}

Errors:
  409 — Wallet already registered
  400 — Invalid role
```

### `POST /api/upload`

Upload and encrypt an EHR file.

```
Request (multipart/form-data):
  file: <binary file>           // Max 10 MB
  patient_wallet: "0x..."       // Patient who will access this file
  keywords: "diabetes,insulin"  // Optional extra keywords
  wallet_address: "0x..."       // Uploader's wallet (must be doctor)

Response (200):
{
  "file_id": "uuid",
  "file_hash": "sha256hex",
  "sse_tags_count": 15,
  "message": "File uploaded and encrypted successfully"
}

Errors:
  403 — Not a doctor / unauthorized
  400 — File too large / no file provided
  500 — Blockchain or DB error
```

### `POST /api/search`

Search encrypted files by keyword.

```
Request Body (JSON):
{
  "keyword": "diabetes",
  "wallet_address": "0x..."
}

Response (200):
{
  "results": [
    {
      "file_id": "uuid",
      "filename": "report.pdf",
      "owner_wallet": "0x...",
      "uploaded_at": "2026-04-22T06:30:00Z"
    }
  ],
  "count": 1
}

Errors:
  400 — Empty keyword
  403 — User not registered
```

### `POST /api/grant-access`

Grant file access to another wallet (owner only).

```
Request Body (JSON):
{
  "file_id": "uuid",
  "owner_wallet": "0x...",
  "grantee_wallet": "0x..."
}

Response (200):
{ "message": "Access granted", "tx_hash": "0x..." }

Errors:
  403 — Not the file owner
  404 — File not found
```

### `POST /api/revoke-access`

Revoke file access (owner only). Same request format as grant.

### `GET /api/check-access/{file_id}/{wallet_address}`

Check if a wallet has access to a file.

```
Response (200):
{ "has_access": true }
```

### `POST /api/decrypt/{file_id}`

Decrypt and return the file.

```
Request Body (JSON):
{
  "wallet_address": "0x..."
}

Response (200): Binary file download

Errors:
  403 — Access denied (smart contract check failed)
  404 — File not found
  500 — Decryption or blockchain error
```

---

## 📜 Smart Contract Interface

### `EHRAccessControl.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EHRAccessControl {

    // ── Storage ──
    struct FileRecord {
        string  fileHash;
        address owner;
        mapping(address => bool) accessList;
    }
    mapping(string => FileRecord) private files;

    // ── Events (Audit Trail) ──
    event FileUploaded(string fileId, string fileHash, address owner, uint256 timestamp);
    event AccessGranted(string fileId, address owner, address grantee, uint256 timestamp);
    event AccessRevoked(string fileId, address owner, address grantee, uint256 timestamp);
    event FileAccessed(string fileId, address user, uint256 timestamp);

    // ── Functions ──

    // Store file hash — called during upload
    function uploadFile(string memory fileId, string memory fileHash) external;

    // Grant access — only file owner can call
    function grantAccess(string memory fileId, address grantee) external;

    // Revoke access — only file owner can call
    function revokeAccess(string memory fileId, address grantee) external;

    // Check if wallet has access — called before decrypt
    function checkAccess(string memory fileId, address user) external view returns (bool);

    // Get stored hash — called to verify integrity
    function getFileHash(string memory fileId) external view returns (string memory);

    // Log file access — called after successful decrypt
    function logAccess(string memory fileId) external;
}
```

---

## 🧭 Key Design Decisions

### 1. Kyber Shared Secret = AES Key

```
Kyber encapsulate(public_key) → (ciphertext, shared_secret)
shared_secret (32 bytes) → used DIRECTLY as AES-256 key
```

No separate key wrapping step. This simplifies the system and is valid for a prototype.

### 2. Single Global SSE Key

```python
SSE_KEY = generate_sse_key()  # stored in backend .env
```

All tags and trapdoors use the same key. In production, per-user keys would be used.

### 3. Persistent Kyber Keypairs

- Generated **once** during user registration
- Public key stored in MongoDB → used by uploader to encrypt for the patient
- Secret key stored in MongoDB (demo only) → used during decryption

### 4. Blockchain Scope

Blockchain handles **ONLY**:
- ✅ File hash (integrity verification)
- ✅ Access control list (who can access which file)
- ✅ Audit events (immutable logs)

Blockchain does **NOT** store:
- ❌ Files or encrypted data
- ❌ Encryption keys

---

## 🧭 Execution Order (STRICT)

```
1. Crypto Module     → AES + Kyber + SSE (no external deps except pip packages)
2. Backend APIs      → FastAPI routes that import crypto
3. MongoDB Setup     → Connect backend to database
4. Blockchain        → Smart contract compile + deploy
5. Integration Test  → Upload → Search → Grant → Decrypt full flow
6. Frontend          → React + MetaMask UI
```

---

## 🚀 Setup & Running

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (local or Atlas)
- MetaMask browser extension

### Step 1 — Clone & Branch

```bash
git clone https://github.com/syedabdulla0710/E-HealthShield.git
cd E-HealthShield
git checkout your-branch-name    # e.g., crypto-setup
```

### Step 2 — Crypto Module

```bash
cd crypto
pip install -r requirements.txt
python -m pytest test_crypto.py -v
```

### Step 3 — Backend

```bash
cd backend
pip install -r requirements.txt
# Edit .env with your MongoDB URI and contract address
uvicorn main:app --reload --port 8000
```

### Step 4 — Blockchain

```bash
cd blockchain
npm install
npx hardhat compile
npx hardhat test
npx hardhat node                      # Start local blockchain
npx hardhat run scripts/deploy.js --network localhost
# Copy deployed contract address to backend/.env
```

### Step 5 — Frontend

```bash
cd frontend
npm install
npm run dev                           # Starts on http://localhost:5173
```

---

## 🔐 Security Notes

> **⚠️ PROTOTYPE DISCLAIMER**
>
> This system is built for academic demonstration.

| Aspect | Demo Approach | Production Approach |
| ------ | ------------- | ------------------- |
| Kyber secret key | Stored in MongoDB | HSM or client-side storage |
| SSE key | Single global key in backend | Per-user or per-session keys |
| Decryption | Server-side | Client-side (browser) |
| File storage | Direct in MongoDB (≤10 MB) | GridFS, IPFS, or cloud storage |
| Blockchain | Hardhat local network | Ethereum mainnet or L2 |

---

## 🔮 Future Scope

- **GridFS / IPFS** for large file storage
- **Client-side decryption** using WebAssembly Kyber
- **Multi-keyword boolean search** (AND/OR queries)
- **File versioning** and update tracking
- **Role hierarchy** (Admin > Doctor > Patient)
- **Mobile app** with React Native
- **Production deployment** with Docker + Kubernetes

---

## 🎯 System Security Goals

```
Confidentiality → AES-256 encryption
Integrity       → Blockchain hash verification
Auditability    → Immutable blockchain event logs
Future Security → Quantum-resistant Kyber encryption
Searchability   → SSE search without decryption
```
