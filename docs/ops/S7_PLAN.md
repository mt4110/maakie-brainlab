# S7: Continuous Integration & Verify (The Safety Net)

## 1. Goal
Establish a robust "Safety Net" that automatically verifies every change to the Evidence Pipeline (S5) and Review Pack (S6).
This ensures that we never break the verification chain and that our artifacts remain reproducible.

## 2. Scope

### In Scope
-   **Automated Verification**: GitHub Actions workflow (`verify_pack.yml`) that runs `make verify-pack` on every push.
-   **Unit Testing**: `test.yml` to run `make test` and `go vet`.
-   **Signing**: GPG signing of Evidence Packs and Review Bundles (Implemented in S7-01).
-   **Documentation**: Updating specs and walkthroughs to reflect these changes.

### Out of Scope (For Now)
-   **Artifact Upload**: We are NOT yet uploading credentials or artifacts to external storage (S3/GCS) in this phase.
-   **Heavy Evals**: We are avoiding heavy LLM evaluations in CI to keep costs/time down.

## 3. Architecture

### 3.1 Signing (S7-01)
-   **Tools**: `cmd/gopsign` (Go-based, portable).
-   **Keys**:
    -   CI uses ephemeral keys generated on-the-fly for verification testing.
    -   Production usage requires `S6_SIGNING_KEY` (private) and `S6_VERIFY_KEY` (public).
-   **Artifacts**: `.asc` detached signatures.

### 3.2 CI Pipeline (S7-02)
-   **Trigger**: Push to `main` or `s7-*`.
-   **Flow**:
    1.  **Test**: Unit tests, Linting.
    2.  **Verify Pack**:
        -   Generate Ephemeral Keys.
        -   Generate Evidence Pack (Signed).
        -   Generate Review Bundle (Signed).
        -   Verify both using `ops/verify_pack.sh`.

## 4. Safety & Security
-   **Keys**: Private keys are NEVER committed. CI uses ephemeral keys or secrets (future).
-   **Git**: `gitignore` must exclude `*.asc` and `*.key`.
-   **Verification**: The `verify_pack.sh` script is the single source of truth for integrity.

## 5. Playbook (If CI Fails)
See `docs/ops/IF_FAIL_S7.md` (Planned).
