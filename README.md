# CyberCamp 7.0 — iOS Reversing Writeups

CyberCamp, now in its 7th edition, took place on the 14th and 15th of
November at INSAT. I took part in the iOS Reversing workshop, and genuinely
enjoyed working through the challenges — one of the tasks even carried the
title **BALD** (my CTF nickname), which was a fun surprise and made the whole
track feel a little more personal.

This repo holds my writeups for the iOS track: six challenges covering IPA
structure, jailbreak/sandbox detection bypasses, custom URL schemes, and
multi-layer crypto/forensics chains on top of iOS app data and backups.

## Challenges

| # | Challenge | Points | Focus |
|---|---|---|---|
| 1 | [IPA Anatomy](./IPA%20Anatomy/Task1_IPA_Anatomy_Writeup.md) | 500 | IPA structure, bundle ID, URL schemes |
| 2 | [Harbor](./Harbor/Task2_Harbor_Writeup.md) | 500 | Jailbreak/Cydia detection, sandbox escape checks |
| 3 | [Waybill](./Waybill/Task3_Waybill_Writeup.md) | 500 | App bundle inspection, hidden secret in app resources |
| 4 | [Sesame](./Sesame/Task4_Sesame_Writeup.md) | 500 | Custom URL scheme handling |
| 5 | [Stortny's Revenge](./Stortny's%20Revenge/writeup/stortnys-revenge-writeup.md) | 700 | Network traffic analysis (Wireshark) + Mach-O reverse engineering, AES-256-CBC, JWT-derived session keys |
| 6 | [Locker](./Locker/locker-writeup/locker-writeup.md) | 600 | Mach-O reverse engineering, multi-layer crypto (XOR/ROT13/AES), iOS backup decryption (PBKDF2 + AES-256-CBC) |

## Repo structure

```
.
├── IPA Anatomy/
│   ├── Task1_IPA_Anatomy_Writeup.md
│   └── images/
├── Harbor/
│   ├── Task2_Harbor_Writeup.md
│   └── images/
├── Waybill/
│   ├── Task3_Waybill_Writeup.md
│   └── images/
├── Sesame/
│   ├── Task4_Sesame_Writeup.md
│   └── images/
├── Stortny's Revenge/
│   └── writeup/
│       ├── stortnys-revenge-writeup.md
│       ├── decrypt.py
│       └── README.md
└── Locker/
    └── locker-writeup/
        ├── locker-writeup.md
        ├── recover_password.py
        ├── decrypt_backup.sh
        └── README.md
```

## Tools used

- **Ghidra** — Mach-O disassembly / decompilation
- **Wireshark** — pcap/HTTP traffic analysis
- **Python** (`cryptography`) — reproducing each app's crypto pipeline
- **OpenSSL** — backup decryption (AES-256-CBC / PBKDF2-SHA256)
- **jq / plutil / strings / otool-equivalents** — plist and binary inspection

## Flags

Flags are intentionally left as spoilers inside each challenge's own writeup
rather than collected here, in case anyone stumbling on this repo wants to
work through the challenges themselves first.

---

Shoutout to the CyberCamp organizers and challenge authors for a genuinely
fun set of iOS challenges — looking forward to the next edition.# CyberCamp-7.0-CTF-tasks-writeup
