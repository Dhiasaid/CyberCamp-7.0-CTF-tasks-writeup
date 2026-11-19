# Stortny's Revenge — Writeup Package

## Contents

- `stortnys-revenge-writeup.md` — the full writeup, ready to fill in with your
  own screenshots and flag.
- `decrypt.py` — standalone decryption script (fill in `session_id`, drop your
  exported `response.bin` next to it, run it).
- `images/` — drop your screenshots here, named to match what the markdown
  file expects. The expected filenames, in order, are:

  | File                              | What to capture                                  |
  |------------------------------------|---------------------------------------------------|
  | `01-unzip-ipa.png`                 | Terminal unzipping the IPA                        |
  | `02-payload-contents.png`          | Directory listing of `Stortny.app/`                |
  | `03-info-plist-ats.png`            | Info.plist, ATS exception domain block             |
  | `04-wireshark-filter.png`          | Wireshark, `http.host == "api.stortny.test"`       |
  | `05-api-secret-request.png`        | The `/api/secret` request + Authorization header   |
  | `06-response-headers.png`          | Follow HTTP Stream, `Content-Type: octet-stream`   |
  | `07-jwt-decoded.png`               | Decoded JWT payload with `sid` highlighted         |
  | `08-export-response-bin.png`       | Exporting the raw response body                    |
  | `09-ghidra-loaded.png`             | Ghidra symbol tree (APIClient/SessionStore/etc.)   |
  | `10-decryptResponse.png`           | `decryptResponse:token:` decompiled                |
  | `11-sessionIDFromToken.png`        | `sessionIDFromToken:` — the `.` split               |
  | `12-base64url-conversion.png`      | Base64URL→Base64 + JSON parse + `sid` lookup       |
  | `13-openData-sessionID.png`        | IV/ciphertext split + key/decrypt calls            |
  | `14-keyForSessionID.png`           | Salt + session ID → SHA-256                        |
  | `15-unmaskSalt.png`                | The XOR unmask loop                                |
  | `16-kMaskedSalt-bytes.png`         | Raw masked salt bytes in Ghidra's hex view         |
  | `17-decrypt-script-output.png`     | Script output printing the decrypted flag          |

Once your images are in place and the flag is filled in, you can export the
markdown to PDF/HTML for submission, or just keep it as-is if the platform
accepts markdown.

## Verified from the provided files (static analysis, no GUI tools)

- `Info.plist`: ATS exception for `stortny.test` with
  `NSExceptionAllowsInsecureHTTPLoads: true`.
- `Stortny` binary: confirms `APIClient`, `SessionStore`, `TransportCipher`
  classes and all the methods referenced in the writeup; confirms the routes
  `/api/secret`, `/api/items/`, `/api/auth/refresh`; and confirms
  `_kMaskedSalt = 6bb1a0957d6f17309fa451d1de5123ae` at address `0x100008400`,
  which unmasks to salt `31eafcc823307751fdc735b4b8364bc7`.
- Not yet verified (needs your `Capture.pcapng`): the JWT / `sid` value and
  the actual `response.bin` contents — grab those in Wireshark following the
  steps in the writeup.
