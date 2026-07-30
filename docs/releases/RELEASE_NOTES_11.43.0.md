# AIOS v11.43.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Sovereign Cross-Chain Blockchain Proof Ledger (`BlockchainProofLedger`)
- Added `BlockchainProofLedger` in `aios_core/blockchain_ledger.py`.
- Records immutable cryptographic state proof hashes onto a blockchain proof ledger.
- REST API: `POST /api/ai/blockchain/record-proof`.
- SDK: `ai_record_blockchain_proof()`.

---

## Test Suite Status
- **4389 passed, 0 failed**
