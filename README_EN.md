# maakie-brainlab

**maakie-brainlab** is a lightweight project for managing code, prompts, and evaluations for the Maakie AI system. It operates via symlinks to `maakie-brainvault` (which contains data, indexes, and models).

> **Note:** This software is currently under active development and is not yet feature-complete.

## Overview & Architecture

The system facilitates execution and evaluation loops for AI agents. It consists of multiple entry points (now unified) and a strict validation mechanism to ensure consistency.

```mermaid
graph TD
    A[User / CI] --> B{il_entry.py (Canonical Entrypoint)}
    B --> C[Guard / Validation]
    B --> D[Execution (il_exec)]
    B --> E[Verification (il_check)]
    C --> F((.local/obs/ Logs))
    D --> F
    E --> F
    
    subgraph Legacy (Forbidden)
    G[il_exec.py] -.-> B
    H[il_check.py] -.-> B
    I[il_guard.py] -.-> B
    end
```

*   **Stopless Architecture**: The system uses a strict "no-exit" policy. Scripts return a `STOP` variable and output `OK`/`ERROR`/`SKIP` logs instead of crashing, allowing for comprehensive auditing.
*   **OBS Logging**: All operations append rigorous logs to `.local/obs/` for traceability.

## Milestones Status

As of February 2026, the project is structured around specific milestones (S21, S22 series). Many core operational foundations have been completed:

*   **Completed (Merged)**: S21-02, S21-03, S21-04, S21-05, S21-06, S21-07, S22-01, S22-03, S22-04, S22-05, S22-06, S22-07, S22-08, S22-09, S22-10, S22-11, S22-12, S22-13, S22-14.
*   **Active / Next Up**: AMBI-01, S21-01, S22-02 (In Review).

## Quickstart

To get started with verifying the system's integrity (Gate-1):

1.  **Clone the repository** (ensure symlinks to `maakie-brainvault` are valid).
2.  **Start the llama-server** (dependency for AI operations).
3.  **Build the index**.
4.  **Run Queries or Verification**:

```bash
# Normal mode (Executes evaluation)
make gate1

# Verification mode (Checks existing results)
bash ops/gate1.sh --verify-only
```

*(If you received a review pack, run `./VERIFY.sh` inside it to check integrity and Gate-1 passes).*

## License

This project is licensed under a **Commercial License**. Unauthorized copying, modification, or distribution is strictly prohibited. (Currently intended for personal/internal use only).
