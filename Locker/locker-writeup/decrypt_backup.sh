#!/usr/bin/env bash
# Locker - decrypt and extract the iOS backup once the password is known.
#
# Usage: ./decrypt_backup.sh backup.enc
set -euo pipefail

ENC_FILE="${1:-backup.enc}"
PASSWORD="Fern-Atlas-4417"   # recovered via recover_password.py

echo "[*] Decrypting $ENC_FILE -> backup.tar"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -md sha256 \
  -in "$ENC_FILE" -out backup.tar -pass pass:"$PASSWORD"

echo "[*] Verifying archive type"
file backup.tar

echo "[*] Extracting to ./extracted_backup"
mkdir -p extracted_backup
tar -xf backup.tar -C extracted_backup

echo "[*] secret.png candidates:"
find extracted_backup -iname "*secret*"

echo
echo "[*] The app's real bundle ID is camp.cyber.locker (see Info.plist)."
echo "    Open: extracted_backup/backup/AppDomain-camp.cyber.locker/Documents/secret.png"
