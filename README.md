# E-HealthShield

A Quantum-Secure and Blockchain-Auditable Framework for Electronic Health Records (EHRs)

---

## 🚀 One-Time Setup (for everyone)

```bash
git clone https://github.com/syedabdulla0710/E-HealthShield.git
cd E-HealthShield
```

---

## 🌿 Branch Usage (IMPORTANT)

Each member must ONLY work on their assigned branch:

### 👨‍🎨 Frontend

```bash
git checkout frontend-setup
```

### ⚙️ Backend

```bash
git checkout backend-setup
```

### ⛓️ Blockchain

```bash
git checkout blockchain-setup
```

### 🔐 Crypto

```bash
git checkout crypto-setup
```

---

## 🔄 Daily Workflow (FOLLOW THIS ALWAYS)

### ✅ Before starting work

```bash
git checkout your-branch-name
git pull origin your-branch-name
```

---

### ✅ After coding (save your work)

```bash
git add .
git commit -m "your message"
git push origin your-branch-name
```

---

## 🔀 Merging to Main (Team Lead / After completion)

1. Go to **GitHub → Pull Requests**
2. Click **New Pull Request**
3. Select:

   * base → `main`
   * compare → your branch
4. Click **Create Pull Request**
5. Click **Merge Pull Request**

---

## 🔁 After Merge (VERY IMPORTANT)

Everyone must update their local code:

```bash
git checkout main
git pull origin main
```

Then go back to your branch:

```bash
git checkout your-branch-name
git merge main
```

---

## ⚠️ Team Rules (DON’T BREAK THESE)

❌ NEVER DO:

```bash
git push origin main
```

✅ ALWAYS:

* Work only on your branch
* Pull before coding
* Push after coding
* Use Pull Requests to merge

---

## 🧠 Simple Flow (REMEMBER THIS)

```
Pull → Code → Add → Commit → Push → PR → Merge
```

---

## 📁 Project Structure

```
E-HealthShield/
│
├── frontend/      # React + Web3 UI
├── backend/       # FastAPI server
├── blockchain/    # Smart contracts (Solidity)
├── crypto/        # AES + Kyber + SSE
└── docs/          # Reports & PPT
```

---

## 👥 Team Members

* Frontend Developer
* Backend Developer
* Blockchain Developer
* Cryptography Developer

---

## 🎯 Project Goal

To build a secure EHR system using:

* AES-256 encryption
* CRYSTALS-Kyber (Post-Quantum Cryptography)
* Searchable Symmetric Encryption (SSE)
* Ethereum Smart Contracts (ACL + Audit Log)

---