#!/usr/bin/env python3
"""
Locker - backup password recovery

Reverses the pipeline found in +[KeyLocker encryptBackupKey:]:
    real_password -> XOR "Vault" -> Base64 -> ROT13 -> AES-128-ECB -> Base64

Requires: cryptography
    pip install cryptography
"""

import base64
import codecs
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# The logged ciphertext from device.log
CIPHERTEXT = "/f0t0Wcc0+bMkPVdUDlyTpXSaGFmCBvvP3wJlwjC/jE="

# Hardcoded in the Locker binary (+[KeyLocker aesEncrypt:])
AES_KEY = b"LockerAESKey2026"

# Hardcoded in the Locker binary (+[KeyLocker xorData:])
XOR_KEY = b"Vault"


def pkcs7_unpad(data: bytes) -> bytes:
    return data[: -data[-1]]


def recover_password(ciphertext_b64: str) -> str:
    # Step 1: outer Base64 decode
    encrypted_data = base64.b64decode(ciphertext_b64)

    # Step 2: AES-128-ECB decrypt (reverses aesEncrypt:)
    cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
    decryptor = cipher.decryptor()
    decrypted = pkcs7_unpad(decryptor.update(encrypted_data) + decryptor.finalize())

    # Step 3: reverse ROT13
    rot = codecs.decode(decrypted.decode("ascii"), "rot_13")

    # Step 4: inner Base64 decode
    xor_data = base64.b64decode(rot)

    # Step 5: reverse the repeating-key XOR (reverses xorData:)
    password = bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(xor_data))

    return password.decode("utf-8")


if __name__ == "__main__":
    pw = recover_password(CIPHERTEXT)
    print("[+] Recovered backup password:", pw)
