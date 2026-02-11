# Provenance Bundle v1 (PB1)

The Provenance Bundle is a single-file transport format that encapsulates an Evidence Pack artifact, its cryptographic signature, the policy used for validation, and the necessary public keys. This self-contained bundle enables **offline verification** and simplifies the transport of trusted artifacts across air-gapped or restricted environments.

## Purpose

- **Offline Verification**: Verify artifacts without extracting them or requiring external configuration.
- **Single-File Transport**: Move `artifact + signature + policy + keys` as one unit.
- **Immutable Context**: The bundle freezes the verification context (policy/keys) at the time of creation.

## Bundle Format

The bundle is a `tar.gz` archive with a strict internal directory structure:

```text
/
├── BUNDLE_VERSION          # Contains "1\n"
├── README.md               # Instructions for manual verification
├── artifact/
│   └── <artifact_name>     # The original Evidence Pack (tar.gz)
├── signature/
│   └── <artifact_name>.sig.json  # Detached S7 signature
├── policy/
│   └── reviewpack_policy.toml    # Policy snapshot
├── keys/
│   └── <key_id>.pub              # Public key(s) needed for verification
└── manifest/
    └── BUNDLE_MANIFEST.tsv # Cryptographic manifest of bundle contents
```

### Constraints
- **Root Files**: Only the directories and files listed above are allowed.
- **Artifact**: Exactly one artifact file in `artifact/`.
- **Signature**: Must match the artifact name with `.sig.json`.
- **Validation**:
  - `BUNDLE_VERSION` must be `1`.
  - `BUNDLE_MANIFEST.tsv` must match content checksums.

## Usage

### Creating a Bundle

Use the `bundle` command to wrap an existing signed artifact:

```bash
evidencepack bundle \
  --artifact stored/packs/my_pack.tar.gz \
  --policy ops/reviewpack_policy.toml \
  --keys-dir ops/keys/reviewpack \
  --out release_bundle.tar.gz
```

Note: The command will automatically locate the signature (`.sig.json`) next to the artifact. If missing, a warning is issued.

### Verifying a Bundle

The `verify` command transparently handles bundles. It detects the format, unpacks it temporarily, and performs verification using the **bundled** policy and keys (unless overridden).

```bash
evidencepack verify --pack release_bundle.tar.gz
```

Output:
```text
Input is a PROVENANCE BUNDLE. Unpacking...
VERIFIED: .../artifact/my_pack.tar.gz
Signature found: .../signature/my_pack.tar.gz.sig.json. Verifying...
Signature VERIFIED.
```

### Overriding Context

You can force verification against a **local** policy or keys instead of the bundled ones:

```bash
# Use local policy, ignore bundled policy
evidencepack verify --pack release_bundle.tar.gz --policy ops/new_policy.toml

# Use local keys, ignore bundled keys
evidencepack verify --pack release_bundle.tar.gz --keys-dir ops/keys/prod
```

## Security Model

1.  **Transport Container**: The bundle is not signed as a whole. It is a container. The security derives from the inner **S7 Signature** on the `artifact`.
2.  **Trust Anchor**: Verification trusts the **Bundle's Keys** by default. Use `--keys-dir` to enforce trust against a different set of keys (e.g., your local trusted ring).
3.  **Tamper Resistance**: The inner artifact is protected by the detached signature. Modifying the artifact invalidates the signature.
