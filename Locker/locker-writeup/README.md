# Locker — Writeup Package

## Contents

- `locker-writeup.md` — the full writeup, ready for your screenshots and already
  filled in with the confirmed password, commands, and flag.
- `recover_password.py` — recovers the backup password from the ciphertext in
  `device.log` (reverses the app's XOR/Base64/ROT13/AES pipeline).
- `decrypt_backup.sh` — decrypts `backup.enc` with the recovered password and
  extracts it, pointing you at the correct `secret.png`.
- `images/` — drop your screenshots here, named to match the writeup.

## Confirmed results (already verified)

| Item | Value |
|---|---|
| AES key (hardcoded, `aesEncrypt:`) | `LockerAESKey2026` (AES-128-ECB) |
| XOR key (hardcoded, `xorData:`) | `Vault` |
| Logged ciphertext | `/f0t0Wcc0+bMkPVdUDlyTpXSaGFmCBvvP3wJlwjC/jE=` |
| Recovered backup password | `Fern-Atlas-4417` |
| Backup cipher | AES-256-CBC, PBKDF2-SHA256, 100000 iterations, openssl-compatible |
| Correct app folder in backup | `AppDomain-camp.cyber.locker` (bundle ID from `Info.plist`) |
| Decoy folder (ignore) | `AppDomain-com.example.notesy` |
| Flag | `Cybercamp{k3y5_1n_th3_m4ch0_unl0ck_th3_v4ult}` (confirmed against your `secret.png`, SHA-256 match) |

## Screenshots to take (in this order)

| # | Filename | What to capture |
|---|---|---|
| 1 | `01-challenge-page.png` | The challenge dashboard entry for "Locker" — description, 600 pts, the 3 files |
| 2 | `02-file-triage.png` | Terminal: `file Locker.ipa device.log backup.enc` |
| 3 | `03-grep-device-log.png` | Terminal: `grep -i "Locker\|encrypt\|backup\|key" device.log` |
| 4 | `04-log-ciphertext-and-format.png` | The two key log lines (CIPHERTEXT + "Backup encrypted with AES-256-CBC...") highlighted |
| 5 | `05-unzip-ipa.png` | Terminal: `unzip Locker.ipa -d extracted` |
| 6 | `06-payload-contents.png` | Directory listing of `extracted/Payload/Locker.app/` |
| 7 | `07-info-plist-bundleid.png` | Info.plist opened, `CFBundleIdentifier: camp.cyber.locker` highlighted |
| 8 | `08-strings-grep.png` | Terminal: `strings Locker \| grep -iE "aes\|vault\|rot\|xor"` |
| 9 | `09-aesEncrypt-decompiled.png` | Ghidra: `+[KeyLocker aesEncrypt:]` decompiled, `CCCrypt()` call with the key arg visible |
| 10 | `10-encryptBackupKey-decompiled.png` | Ghidra: `+[KeyLocker encryptBackupKey:]` decompiled, showing the call order (xor → base64 → rot13 → aes → base64) |
| 11 | `11-xorData-decompiled.png` | Ghidra: `+[KeyLocker xorData:]` decompiled, the `"Vault"` key visible |
| 12 | `12-password-script-output.png` | Terminal running `recover_password.py`, printing `Fern-Atlas-4417` |
| 13 | `13-openssl-decrypt.png` | Terminal running the `openssl enc -d -aes-256-cbc -pbkdf2 ...` command, no errors |
| 14 | `14-file-backup-tar.png` | Terminal: `file backup.tar` → `POSIX tar archive` |
| 15 | `15-tar-extract.png` | Terminal extracting the tar and listing its contents |
| 16 | `16-two-secret-png.png` | Directory listing showing both `AppDomain-camp.cyber.locker` and `AppDomain-com.example.notesy`, each with a `secret.png` |
| 17 | `17-secret-png-opened.png` | The correct `secret.png` opened, flag visible |

Once the images are dropped in with those filenames and you're happy with the
text, export the markdown to PDF/HTML for submission (or submit as-is if the
platform accepts markdown).
