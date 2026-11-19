# Stortny's Revenge — Writeup

**Category:** Rev / Forensics (iOS)
**Files provided:** `Stortny.ipa`, `Capture.pcapng`

## Challenge Overview

We're given two files:

- `Stortny.ipa` — an iOS application package.
- `Capture.pcapng` — a network capture taken while the app was running.

The goal is to figure out how the app talks to its backend, how the data in transit
is protected, and ultimately recover the hidden flag.

This splits into two halves:

1. Traffic analysis — what does the app actually send and receive?
2. Reverse engineering — how does the app encrypt/decrypt that data?

---

## 1. Extracting the IPA

An `.ipa` is just a zip archive, so:

```bash
unzip Stortny.ipa -d Extracted
```

![Unzipping the IPA](images/01-unzip-ipa.png)
*Screenshot: terminal running the unzip command.*

![Payload contents](images/02-payload-contents.png)
*Screenshot: directory listing of `Extracted/Payload/Stortny.app/` showing `Info.plist`,
`PkgInfo`, and the `Stortny` executable.*

---

## 2. Info.plist — the App Transport Security clue

Before touching the binary, `Info.plist` is worth a look. The relevant block:

```json
"NSAppTransportSecurity": {
  "NSExceptionDomains": {
    "stortny.test": {
      "NSExceptionAllowsInsecureHTTPLoads": true,
      "NSIncludesSubdomains": true
    }
  }
}
```

![Info.plist ATS exception](images/03-info-plist-ats.png)
*Screenshot: Info.plist opened (Xcode / `plutil -p` / a plist viewer), with the
`NSAppTransportSecurity` → `stortny.test` block highlighted.*

This tells us the app is explicitly allowed to talk to `api.stortny.test` over
**plain HTTP** — which is exactly why we can read the requests directly in
Wireshark without dealing with TLS. It doesn't mean the *payloads* are readable
though — the app adds its own encryption layer on top, which is the part we
still have to reverse.

---

## 3. Traffic Analysis in Wireshark

Open `Capture.pcapng` and apply:

```
http.host == "api.stortny.test"
```

![Wireshark filter applied](images/04-wireshark-filter.png)
*Screenshot: the filtered packet list.*

Among the requests, one stands out:

```
GET /api/secret HTTP/1.1
Host: api.stortny.test
Authorization: Bearer <JWT>
```

![The /api/secret request](images/05-api-secret-request.png)
*Screenshot: the request pane showing the method, path, and the
`Authorization: Bearer ...` header.*

Following the HTTP stream, the response comes back as:

```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Length: 528
```

![Response headers](images/06-response-headers.png)
*Screenshot: Follow HTTP Stream view, highlighting `Content-Type: application/octet-stream`
and the body length.*

`application/octet-stream` means this is raw binary, not something we can read
directly — we need to understand the app's decryption logic first.

### Decoding the JWT

The `Authorization` header carries a standard three-part JWT
(`HEADER.PAYLOAD.SIGNATURE`). Decoding the payload (Base64URL, same way the app
does internally) gives a `sid` claim:

```json
{ "sid": "sess_XXXXXXXXXX", ... }
```

![JWT payload decoded](images/07-jwt-decoded.png)
*Screenshot: the JWT payload decoded (jwt.io, CyberChef, or a one-liner), with the
`sid` field highlighted.*

Record this session ID — it's the second ingredient (with the salt) for the AES key.

### Exporting the encrypted body

Export the raw response body (not the HTTP headers) as `response.bin`:

- Wireshark: select the response packet → *Follow → HTTP Stream* → set to show
  only the response → *Save As*, or
- *File → Export Packet Dissections*, or right-click the data → *Export Packet Bytes*.

![Exporting response.bin](images/08-export-response-bin.png)
*Screenshot: the export dialog / confirmation that `response.bin` was saved,
ideally showing its size (528 bytes in this build).*

---

## 4. Reverse Engineering the Binary

Load `Extracted/Payload/Stortny.app/Stortny` into Ghidra (or Hopper/IDA).

![Binary loaded in Ghidra](images/09-ghidra-loaded.png)
*Screenshot: the Symbol Tree showing the `APIClient`, `SessionStore`, and
`TransportCipher` Objective-C classes.*

Static analysis of the executable (string table + symbol table) confirms the
following methods exist, matching what's visible in the decompiler:

```
-[APIClient decryptResponse:token:]
-[APIClient encryptBody:token:]
+[SessionStore sessionIDFromToken:]
+[TransportCipher openData:sessionID:]
+[TransportCipher sealData:sessionID:]
+[TransportCipher keyForSessionID:]
+[TransportCipher unmaskSalt]
+[TransportCipher aes256CBCDecrypt:key:iv:]
```

The binary's string table also reveals the backend routes it talks to:

```
http://api.stortny.test
/api/secret
/api/items/
/api/auth/refresh
```

### 4.1 `decryptResponse:token:` — the entry point

![decryptResponse:token: decompiled](images/10-decryptResponse.png)
*Screenshot: decompiled view showing the call into `sessionIDFromToken:`, then
passing the response + session ID into `openData:sessionID:`.*

This method is the overall flow controller: extract the session ID from the
token, then hand the response and session ID to `TransportCipher` for decryption.

### 4.2 `sessionIDFromToken:` — pulling `sid` out of the JWT

![sessionIDFromToken: decompiled](images/11-sessionIDFromToken.png)
*Screenshot: decompiled view showing the `.`-split into exactly 3 parts.*

![Base64URL to Base64 conversion](images/12-base64url-conversion.png)
*Screenshot: decompiled view of the character substitution (`-`→`+`, `_`→`/`),
padding being added, the payload being base64-decoded, parsed as JSON, and the
`sid` key being looked up (and type-checked as a string).*

Key takeaway: the app doesn't use the whole JWT for crypto — only the `sid`
claim, extracted exactly the way shown above.

### 4.3 `openData:sessionID:` — splitting IV and ciphertext

![openData:sessionID: decompiled](images/13-openData-sessionID.png)
*Screenshot: decompiled view showing the length check, the first 16 bytes being
taken as the IV, the remainder as ciphertext, and the call to
`keyForSessionID:` followed by `aes256CBCDecrypt:key:iv:`.*

So the response layout is:

```
[ 16-byte IV ][ ciphertext ... ]
```

and the algorithm is **AES-256-CBC**.

### 4.4 `keyForSessionID:` — deriving the AES key

![keyForSessionID: decompiled](images/14-keyForSessionID.png)
*Screenshot: decompiled view showing `unmaskSalt` being called, the session ID
bytes being appended to the salt, and the combined buffer being hashed with
SHA-256.*

```
key = SHA256(salt || session_id_utf8)
```

SHA-256 produces a 32-byte digest — exactly the key size AES-256 needs.

### 4.5 `unmaskSalt` — recovering the salt

![unmaskSalt: decompiled](images/15-unmaskSalt.png)
*Screenshot: decompiled view of the XOR loop, e.g.:*

```c
for (i = 0; i < 0x10; i++) {
    salt[i] = (&_kMaskedSalt)[i] ^ (char)(i + 0x5a);
}
```

![_kMaskedSalt raw bytes](images/16-kMaskedSalt-bytes.png)
*Screenshot: the hex view / data listing of `_kMaskedSalt` in Ghidra's memory map.*

Confirmed directly from the binary's `__TEXT.__const` section (symbol
`_kMaskedSalt`, address `0x100008400`):

```
6b b1 a0 95 7d 6f 17 30 9f a4 51 d1 de 51 23 ae
```

Reproducing the unmask in Python:

```python
masked_salt = bytes.fromhex(
    "6bb1a0957d6f17309fa451d1de5123ae"[:32]
)

salt = bytes(
    byte ^ ((i + 0x5A) & 0xFF)
    for i, byte in enumerate(masked_salt)
)

print("Salt:", salt.hex())
```

Recovered salt:

```
31eafcc823307751fdc735b4b8364bc7
```
*(16 bytes — trim/verify against your own Ghidra hex dump if your build differs.)*

---

## 5. Putting It Together

Everything needed to reproduce the decryption:

| Ingredient     | Value / Source                                   |
|----------------|---------------------------------------------------|
| Session ID     | `sid` claim from the JWT in the `/api/secret` request |
| Masked salt    | `_kMaskedSalt` in the binary (`6bb1a0957d6f17309fa451d1de5123ae`) |
| Salt           | masked salt XOR'd with `(index + 0x5A)` per byte  |
| Key derivation | `SHA256(salt + session_id)`                        |
| Response layout| first 16 bytes = IV, rest = ciphertext             |
| Algorithm      | AES-256-CBC, PKCS7 padding                         |

### Decryption script

See `decrypt.py` in this archive — fill in your own `session_id` (from the JWT)
and point it at your exported `response.bin`.

```python
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Session ID extracted from the JWT payload (fill in your own)
session_id = "sess_XXXXXXXXXX"

# Masked salt recovered from the iOS binary (_kMaskedSalt)
masked_salt = bytes.fromhex("6bb1a0957d6f17309fa451d1de5123ae"[:32])

# Reproduce unmaskSalt()
salt = bytes(b ^ ((i + 0x5A) & 0xFF) for i, b in enumerate(masked_salt))

# Reproduce keyForSessionID()
key = hashlib.sha256(salt + session_id.encode("utf-8")).digest()

with open("response.bin", "rb") as f:
    response = f.read()

iv, ciphertext = response[:16], response[16:]

# Reproduce openData:sessionID:
cipher = AES.new(key, AES.MODE_CBC, iv)
plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)

print(plaintext.decode("utf-8"))
```

![Running the decryption script](images/17-decrypt-script-output.png)
*Screenshot: terminal running the script and printing the decrypted flag.*

---

## Flag

```
<paste your decrypted flag here>
```

## Takeaways

- `NSAppTransportSecurity` exceptions are worth checking first — they tell you
  immediately whether traffic will be plaintext HTTP or TLS.
- An app-level crypto layer on top of HTTP means Wireshark alone isn't enough;
  you need the binary to recover the algorithm and key material.
- "Masking" a constant with a simple XOR doesn't add real security — once the
  mask operation is visible in the decompiler, the original value falls right out.
- Deriving a key from a per-session value (the JWT's `sid`) plus a fixed salt
  means capturing a single valid session is enough to decrypt that session's traffic.
