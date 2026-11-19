# Locker — Writeup

**Category:** iOS Reverse Engineering / Cryptography / Backup Forensics
**Points:** 600
**Files provided:** `Locker.ipa`, `backup.enc`, `device.log`

## Challenge Overview

> Locker keeps private notes and photos behind a password. Its owner made an
> encrypted backup of the phone, and we pulled the device log the same
> evening. The backup password isn't written down anywhere, but the app
> logged something about it.
>
> Get into the backup and find what Locker was protecting.
>
> Flag format: `Cybercamp{...}`

![Challenge description](images/01-challenge-page.png)
*Screenshot: the challenge page showing the description, points (600), and the
three provided files (`backup.enc`, `device.log`, `Locker.ipa`).*

Three files, three jobs:

1. **`Locker.ipa`** — the app, which we need to reverse to learn how the
   backup password was derived/obfuscated.
2. **`device.log`** — a device log captured the same evening, which leaks an
   *encrypted* copy of that password.
3. **`backup.enc`** — the actual encrypted iOS backup we need to open.

---

## 1. Initial File Triage

```bash
file Locker.ipa device.log backup.enc
```

![file command on the three inputs](images/02-file-triage.png)
*Screenshot: terminal output of `file` on all three provided files — note
`backup.enc` reports as `openssl enc'd data with salted password`.*

---

## 2. Reading the Device Log

`device.log` is long, so instead of `cat`-ing the whole thing, grep for the
app name and anything crypto-related:

```bash
grep -i "Locker\|encrypt\|backup\|key" device.log
```

![Grepping device.log](images/03-grep-device-log.png)
*Screenshot: terminal showing the filtered log lines.*

Two lines matter:

```
Locker(Foundation)[1520] <Notice>: Key encrypted, investigate the Mach-O! CIPHERTEXT: "/f0t0Wcc0+bMkPVdUDlyTpXSaGFmCBvvP3wJlwjC/jE="
Locker(Foundation)[1520] <Notice>: Backup encrypted with AES-256-CBC, key from the backup password (PBKDF2-SHA256, 100000 iterations), openssl-compatible
```

![The two key log lines](images/04-log-ciphertext-and-format.png)
*Screenshot: these two lines highlighted in the log — the encrypted password
blob, and the exact backup encryption parameters.*

So:
- The app logs an **encrypted copy of the real backup password** — the log
  text ("investigate the Mach-O") is a direct pointer to go reverse the binary.
- The backup itself is AES‑256‑CBC, key derived via **PBKDF2‑SHA256 /
  100,000 iterations**, in an **OpenSSL‑compatible** container (i.e. decryptable
  with the standard `openssl enc -pbkdf2` command once we have the password).

---

## 3. Extracting the IPA

```bash
unzip Locker.ipa -d extracted
```

![Unzipping the IPA](images/05-unzip-ipa.png)
*Screenshot: terminal running the unzip.*

The executable lives at `extracted/Payload/Locker.app/Locker`.

![Payload contents](images/06-payload-contents.png)
*Screenshot: directory listing showing `Locker.app/` and the `Locker` executable inside.*

Checking the app's `Info.plist` confirms the bundle identifier — this matters
later, to pick the right app folder inside the decrypted backup:

```json
"CFBundleIdentifier": "camp.cyber.locker"
```

![Info.plist bundle identifier](images/07-info-plist-bundleid.png)
*Screenshot: Info.plist opened, `CFBundleIdentifier` highlighted.*

---

## 4. Reverse Engineering the Mach-O

Load `Locker` into Ghidra. Rather than reading every function, search strings
for anything crypto-flavored (`Aes`, `Vault`, `rot13`, `xorData` all hit):

```bash
strings Locker | grep -iE "aes|vault|rot|xor"
```

![strings grep on the binary](images/08-strings-grep.png)
*Screenshot: terminal output showing the hits — `LockerAESKey2026`, `Vault`,
`rot13:`, `xorData:`, `aesEncrypt:`, `_CCCrypt`.*

This confirms, directly from the binary's symbol/string tables, everything
needed to reverse the log's ciphertext:

```
+[KeyLocker aesEncrypt:]
+[KeyLocker rot13:]
+[KeyLocker xorData:]
+[KeyLocker encryptBackupKey:]
+[KeyLocker logBackupKey:]
LockerAESKey2026
Vault
_CCCrypt
```

### 4.1 `aesEncrypt:` — the hardcoded AES key

![aesEncrypt: decompiled](images/09-aesEncrypt-decompiled.png)
*Screenshot: decompiled `+[KeyLocker aesEncrypt:]`, showing the call into
`CCCrypt()` with the key argument and key-length argument visible.*

The key is passed as a literal string, `LockerAESKey2026` (16 bytes → AES‑128),
and the mode/key-size arguments confirm **AES‑128‑ECB**.

### 4.2 `encryptBackupKey:` — the full pipeline

![encryptBackupKey: decompiled](images/10-encryptBackupKey-decompiled.png)
*Screenshot: decompiled `+[KeyLocker encryptBackupKey:]`, showing the call
order: `xorData:` → `base64:` → `rot13:` → `aesEncrypt:` → `base64:`.*

### 4.3 `xorData:` — the XOR key

![xorData: decompiled](images/11-xorData-decompiled.png)
*Screenshot: decompiled `+[KeyLocker xorData:]`, showing the repeating XOR
key string `Vault` being used byte-by-byte against the input.*

### What we now know

```
real_password
   --XOR "Vault" (repeating key)-->
   --Base64 encode-->
   --ROT13-->
   --AES-128-ECB encrypt, key "LockerAESKey2026"-->
   --Base64 encode-->
CIPHERTEXT (the string logged in device.log)
```

To recover the password we just run this backward.

---

## 5. Recovering the Backup Password

```python
import base64, codecs
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

CIPHERTEXT = "/f0t0Wcc0+bMkPVdUDlyTpXSaGFmCBvvP3wJlwjC/jE="
AES_KEY = b"LockerAESKey2026"
XOR_KEY = b"Vault"

def pkcs7_unpad(data):
    return data[:-data[-1]]

# Step 1: outer Base64 decode
encrypted_data = base64.b64decode(CIPHERTEXT)

# Step 2: AES-128-ECB decrypt (reverses aesEncrypt:)
cipher = Cipher(algorithms.AES(AES_KEY), modes.ECB())
d = cipher.decryptor()
decrypted = pkcs7_unpad(d.update(encrypted_data) + d.finalize())

# Step 3: reverse ROT13
rot = codecs.decode(decrypted.decode("ascii"), "rot_13")

# Step 4: inner Base64 decode
xor_data = base64.b64decode(rot)

# Step 5: reverse the repeating-key XOR (reverses xorData:)
password = bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(xor_data))

print("Recovered password:", password.decode("utf-8"))
```

![Running the password-recovery script](images/12-password-script-output.png)
*Screenshot: terminal running the script above.*

**Recovered backup password: `Fern-Atlas-4417`**

---

## 6. Decrypting the Backup

`device.log` already told us the exact parameters: AES‑256‑CBC, key from
PBKDF2‑SHA256 with 100,000 iterations, OpenSSL‑compatible container. That
means the standard `openssl enc` command can decrypt it directly — no need to
hand-roll key derivation:

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -md sha256 \
  -in backup.enc -out backup.tar -pass pass:'Fern-Atlas-4417'
```

![Decrypting backup.enc](images/13-openssl-decrypt.png)
*Screenshot: terminal running the command above with no errors.*

```bash
file backup.tar
```

![Confirming backup.tar](images/14-file-backup-tar.png)
*Screenshot: `file backup.tar` reporting `POSIX tar archive` — confirms the
password and parameters were correct.*

---

## 7. Extracting the Backup

```bash
tar -xf backup.tar -C extracted_backup
find extracted_backup -iname "*secret*"
```

![Extracting the tar](images/15-tar-extract.png)
*Screenshot: terminal extracting the tar and listing its contents.*

Two `secret.png` files turn up:

```
AppDomain-camp.cyber.locker/Documents/secret.png
AppDomain-com.example.notesy/Documents/secret.png
```

![Two secret.png candidates](images/16-two-secret-png.png)
*Screenshot: directory listing showing both `AppDomain-*` folders with their
`secret.png` files.*

This is a deliberate decoy — `com.example.notesy` is an unrelated app bundled
into the same backup. Recall from step 3 that `Locker`'s real bundle
identifier is `camp.cyber.locker`, so the correct file is the one under
**`AppDomain-camp.cyber.locker`**.

---

## 8. The Flag

![Opening the correct secret.png](images/17-secret-png-opened.png)
*Screenshot: the `secret.png` from `AppDomain-camp.cyber.locker/Documents/`
opened, showing the note and the flag.*

```
Cybercamp{k3y5_1n_th3_m4ch0_unl0ck_th3_v4ult}
```

---

## Takeaways

- A log line that casually says "investigate the Mach‑O" is a direct hint
  that the real secret lives in the binary, not the log itself.
- Multiple layers of XOR/ROT13/Base64/AES stacked together don't add real
  security if every key is a hardcoded string sitting in the binary's string
  table — `strings` + a quick grep got us 90% of the way there.
- When a log/app explicitly states a standard KDF and cipher (PBKDF2‑SHA256,
  AES‑256‑CBC, "openssl‑compatible"), it's usually faster to just hand the
  password straight to `openssl enc -pbkdf2` than to reimplement the key
  derivation by hand.
- Decoy files with the same name in different `AppDomain-*` folders are a
  common forensics trick — always cross-check against the real bundle
  identifier from `Info.plist` before trusting a filename.
