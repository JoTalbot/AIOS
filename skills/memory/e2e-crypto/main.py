#!/usr/bin/env python3
"""Octopus E2E Encryption (Instruction #54)
Production: AES-256-GCM via WebCrypto API.
Python fallback: Fernet-compatible placeholder.
"""
import os, base64
from cryptography.fernet import Fernet

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def encrypt(data_bytes, key_b64):
    f = Fernet(key_b64)
    return f.encrypt(data_bytes).decode()

def decrypt(token, key_b64):
    f = Fernet(key_b64)
    return f.decrypt(token.encode()).decode()

if __name__ == '__main__':
    key = generate_key()
    data = b'Octopus Memory Secret'
    enc = encrypt(data, key)
    dec = decrypt(enc, key)
    print({'ok': data == dec, 'key_len': len(key), 'encrypted': enc[:20]})
