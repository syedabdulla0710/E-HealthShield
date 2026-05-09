# ⚙️ Backend Module — FastAPI Server

The backend is the central hub of E-HealthShield. It exposes REST APIs that
connect the **React frontend**, the **crypto engine**, and the **blockchain**
into a single, cohesive system.

---

## 🏗️ Architecture

```
Frontend (React)
    │
    ▼
┌─────────────────────────────────────────────┐
│  FastAPI Backend  (this module)              │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Auth    │  │  Upload  │  │  Search   │ │
│  │  Route   │  │  Route   │  │  Route    │ │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘ │
│       │              │              │       │
│  ┌────┴──────────────┴──────────────┴─────┐ │
│  │         Crypto Module (import)         │ │
│  │  AES-256-GCM │ Kyber-768 │ SSE (HMAC) │ │
│  └────────────────────────────────────────┘ │
│       │              │              │       │
│  ┌────┴─────┐  ┌─────┴────┐  ┌─────┴─────┐ │
│  │ MongoDB  │  │Blockchain│  │  Logger   │ │
│  │ (Atlas)  │  │ (Stub)   │  │           │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
backend/
├── main.py               # FastAPI app — CORS, lifespan, route registration
├── config.py             # Pydantic settings loaded from .env
├── database.py           # Motor async MongoDB client + indexes
├── blockchain_client.py  # Blockchain stub (MongoDB-backed, swappable to Web3)
├── logger.py             # Structured logging (console + logs/app.log)
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (MongoDB URI, SSE key, etc.)
│
└── routes/
    ├── __init__.py
    ├── auth.py           # POST /api/register
    ├── upload.py         # POST /api/upload
    ├── search.py         # POST /api/search
    ├── access.py         # POST /api/grant-access, /revoke-access, /check-access
    └── decrypt.py        # POST /api/decrypt/{file_id}
```

---

## 🚀 How to Run

```bash
# From project root (E-HealthShield/)

# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Configure .env (already set up with Atlas)
# Edit backend/.env if you need to change MongoDB URI or SSE key

# 3. Start the server
python -m uvicorn backend.main:app --reload --port 8000

# 4. Open API docs
# Swagger UI:  http://localhost:8000/docs
# ReDoc:       http://localhost:8000/redoc
```

> **Note:** The server requires MongoDB to be reachable. We use MongoDB Atlas
> (free tier), so no local installation is needed.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check — returns `{"status": "healthy"}` |
| `POST` | `/api/register` | Register user + generate Kyber keypair |
| `POST` | `/api/upload` | Upload, encrypt, and store an EHR file |
| `POST` | `/api/search` | Search encrypted files by keyword (SSE) |
| `POST` | `/api/grant-access` | Grant file access to another wallet |
| `POST` | `/api/revoke-access` | Revoke file access |
| `GET`  | `/api/check-access/{file_id}/{wallet}` | Check if wallet has access |
| `POST` | `/api/decrypt/{file_id}` | Decrypt and download a file |

---

## 🔄 How Each Endpoint Works

### `POST /api/register`

Registers a new user (doctor or patient) and generates a persistent
CRYSTALS-Kyber keypair.

```
Request:  { "wallet_address": "0x...", "role": "doctor" }
Response: { "wallet_address": "...", "role": "...", "kyber_public_key": "...", "message": "..." }
Errors:   409 (already registered), 400 (invalid role)
```

**Flow:**
1. Validate wallet format (42-char hex starting with `0x`) and role
2. Check if wallet already exists in MongoDB → 409 if duplicate
3. Call `crypto.generate_keypair()` → Kyber-768 public + secret key
4. Store user document in MongoDB (keys are base64-encoded)

---

### `POST /api/upload`

Encrypts and stores an EHR file. Only doctors can upload.

```
Request:  multipart/form-data
  - file: <binary>                    (max 10 MB)
  - wallet_address: "0x..."           (must be a doctor)
  - patient_wallet: "0x..."           (patient who will access this file)
  - keywords: "diabetes,insulin"      (optional extra keywords)

Response: { "file_id": "uuid", "file_hash": "sha256...", "sse_tags_count": 18, "message": "..." }
Errors:   403 (not a doctor), 400 (file too large), 404 (patient not found)
```

**Flow:**
1. Verify uploader is a registered doctor
2. Verify patient wallet exists in DB
3. Read file → check size (max 10 MB)
4. `crypto.extract_keywords()` → auto-extract keywords from file content
5. Merge with optional manual keywords
6. `crypto.generate_tags(sse_key, keywords)` → HMAC-SHA256 SSE tags
7. Fetch patient's Kyber public key from DB
8. `crypto.encapsulate(patient_pk)` → `(kyber_ciphertext, shared_secret)`
9. `crypto.encrypt_file(file_bytes, shared_secret)` → AES-256-GCM `{ciphertext, nonce, tag}`
10. `crypto.compute_file_hash(file_bytes)` → SHA-256 hash
11. Store encrypted bundle in MongoDB (all binary fields base64-encoded)
12. Record file hash on blockchain + auto-grant access to owner & patient
13. Log the upload event

---

### `POST /api/search`

Searches encrypted files by keyword using SSE — **no decryption needed**.

```
Request:  { "keyword": "diabetes", "wallet_address": "0x..." }
Response: { "results": [{ "file_id": "...", "filename": "...", ... }], "count": 1 }
Errors:   400 (empty keyword), 403 (not registered)
```

**Flow:**
1. `crypto.generate_trapdoor(sse_key, keyword)` → HMAC tag (trapdoor)
2. Query MongoDB: find documents where `sse_tags` array contains the trapdoor
3. Filter results to files the user is associated with (owner or patient)
4. Return matching file metadata

---

### `POST /api/grant-access` / `/api/revoke-access`

Manage file access. Only the file owner can grant or revoke.

```
Request:  { "file_id": "uuid", "owner_wallet": "0x...", "grantee_wallet": "0x..." }
Response: { "message": "Access granted/revoked", "tx_hash": "0x..." }
Errors:   403 (not owner), 404 (file not found)
```

---

### `POST /api/decrypt/{file_id}`

Decrypts and returns the original file as a download.

```
Request:  { "wallet_address": "0x..." }
Response: Binary file download (with Content-Disposition header)
Errors:   403 (access denied), 404 (file not found), 500 (integrity check failed)
```

**Flow:**
1. Verify file exists in MongoDB
2. Check access via blockchain (`blockchain_client.check_access()`)
3. Fetch patient's Kyber secret key from DB
4. `crypto.decapsulate(kyber_ct, secret_key)` → recover shared secret
5. `crypto.decrypt_file(ciphertext, shared_secret, nonce, tag)` → plaintext
6. **Integrity check:** `SHA-256(plaintext) == stored_hash` — fails if tampered
7. Log the access event on blockchain (audit trail)
8. Return file as streaming response

---

## 🗄️ MongoDB Collections

### `users`
```json
{
  "wallet_address": "0xabc...",
  "role": "doctor",
  "kyber_public_key": "<base64>",
  "kyber_secret_key": "<base64>",
  "registered_at": "2026-05-09T..."
}
```

### `encrypted_files`
```json
{
  "file_id": "uuid",
  "filename": "patient_report.pdf",
  "owner_wallet": "0x...",
  "patient_wallet": "0x...",
  "encrypted_data": "<base64 AES ciphertext>",
  "aes_nonce": "<base64>",
  "aes_tag": "<base64>",
  "kyber_ciphertext": "<base64>",
  "sse_tags": ["hmac_hex_1", "hmac_hex_2", ...],
  "file_hash": "sha256hex",
  "file_size": 245000,
  "uploaded_at": "2026-05-09T..."
}
```

### `blockchain_records` (stub)
```json
{
  "file_id": "uuid",
  "file_hash": "sha256hex",
  "owner": "0x...",
  "access_list": ["0x...", "0x..."],
  "audit_log": [{ "user": "0x...", "action": "accessed", "timestamp": "..." }]
}
```

---

## 🔐 Security Notes

| Aspect | Current (Demo) | Production |
|--------|---------------|------------|
| Kyber secret key | Stored in MongoDB | HSM or client-side |
| SSE key | Single global key in `.env` | Per-user keys |
| Decryption | Server-side | Client-side (browser) |
| Blockchain | MongoDB stub | Real smart contract (Web3.py) |
| File storage | Direct in MongoDB (max 10 MB) | GridFS / IPFS |
| Authentication | Wallet address only | Signed messages + nonce |

---

## 🧩 Key Design Decisions

1. **Kyber shared secret = AES key**: The 32-byte shared secret from Kyber
   encapsulation is used directly as the AES-256 key. No separate key wrapping.

2. **Blockchain stub**: `blockchain_client.py` uses MongoDB to simulate
   on-chain operations. The API surface is identical to the Solidity contract,
   so swapping to Web3.py requires **zero route changes**.

3. **SSE tag as array index**: Tags are stored as a MongoDB array with an index,
   enabling efficient `{"sse_tags": trapdoor}` queries for search.

4. **Base64 encoding**: All binary data (keys, ciphertext, nonces) is
   base64-encoded before storage for JSON/MongoDB compatibility.

---

## 📋 Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | Atlas cluster URI |
| `MONGO_DB_NAME` | Database name | `e_healthshield` |
| `SSE_KEY` | Base64-encoded 32-byte SSE master key | Auto-generated |
| `CONTRACT_ADDRESS` | Smart contract address (future) | Empty |
| `BLOCKCHAIN_RPC_URL` | Ethereum RPC URL | `http://127.0.0.1:8545` |
| `MAX_FILE_SIZE_MB` | Upload file size limit | `10` |
