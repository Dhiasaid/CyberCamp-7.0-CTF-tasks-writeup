#!/usr/bin/env python3
"""
Stortny's Revenge - response decryption

Fill in `session_id` with the `sid` claim from the JWT found in the
Authorization header of the /api/secret request (see Capture.pcapng),
and place the exported HTTP response body next to this script as
`response.bin` (headers stripped, raw bytes only).

Requires: pycryptodome
    pip install pycryptodome
"""

import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# --- Fill this in from the JWT payload in the pcap ---
session_id = "sess_XXXXXXXXXX"

# --- Masked salt, recovered from the Stortny binary's _kMaskedSalt symbol ---
MASKED_SALT = bytes.fromhex("6bb1a0957d6f17309fa451d1de5123ae"[:32])


def unmask_salt(masked: bytes) -> bytes:
    """Reproduces +[TransportCipher unmaskSalt]"""
    return bytes(b ^ ((i + 0x5A) & 0xFF) for i, b in enumerate(masked))


def key_for_session_id(session_id: str) -> bytes:
    """Reproduces +[TransportCipher keyForSessionID:]"""
    salt = unmask_salt(MASKED_SALT)
    return hashlib.sha256(salt + session_id.encode("utf-8")).digest()


def open_data(response: bytes, session_id: str) -> bytes:
    """Reproduces +[TransportCipher openData:sessionID:]"""
    iv, ciphertext = response[:16], response[16:]
    key = key_for_session_id(session_id)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)


if __name__ == "__main__":
    with open("response.bin", "rb") as f:
        response = f.read()

    plaintext = open_data(response, session_id)
    print(plaintext.decode("utf-8"))
