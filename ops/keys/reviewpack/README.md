# Review Pack Public Keys

This directory contains the public keys used to verify signatures on evidence packs.

## Format
- Each file must be named `<key_id>.pub`.
- The content must be a JSON object matching the `CryptoKey` struct in `cmd/evidencepack/crypto.go`.

Example:
```json
{
  "key_id": "production-key-v1",
  "alg": "ed25519",
  "pub_b64": "<base64_encoded_public_key>"
}
```

## Adding a Key
1. Generate a new Ed25519 key pair.
2. Store the private key securely (e.g., in a secret manager or offline storage). **Do not commit private keys to this repository.**
3. Create the `<key_id>.pub` file here with the public key information.
4. Commit the public key file.
