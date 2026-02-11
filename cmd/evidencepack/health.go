package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ---------------------------------------------------------------------------
// evidencepack health — local chain diagnostics
// ---------------------------------------------------------------------------

const (
	// CmdHealth is the subcommand name.
	CmdHealth = "health"
)

// ExitCode constants for health and verify subcommands.
const (
	ExitOK           = 0
	ExitTamper       = 2
	ExitSpecMismatch = 3
	ExitIOError      = 4
)

// HealthError wraps an error with a specific exit code.
type HealthError struct {
	Code    int
	Message string
}

func (e *HealthError) Error() string { return e.Message }

func runHealth(args []string) error {
	fs := flag.NewFlagSet("health", flag.ExitOnError)
	repoRoot := fs.String("repo", ".", "Repository root directory")
	jsonOut := fs.Bool("json", false, "Output diagnostics as JSON (P1)")
	_ = jsonOut // P1: reserved for future use

	if err := fs.Parse(args); err != nil {
		return err
	}

	chainPath := filepath.Join(*repoRoot, ChainDir, ChainFile)
	return runHealthCheck(chainPath)
}

func runHealthCheck(chainPath string) error {
	fmt.Println("=== Audit Chain Health Check ===")
	fmt.Printf("Chain: %s\n\n", chainPath)

	// Check 1: chain file exists
	info, err := os.Stat(chainPath)
	if os.IsNotExist(err) {
		return reportMissingChain(chainPath)
	}
	if err != nil {
		fmt.Printf("[FAIL] Cannot read chain file: %v\n", err)
		return &HealthError{Code: ExitIOError, Message: err.Error()}
	}
	fmt.Printf("[OK]   Chain file exists (%d bytes)\n", info.Size())

	// Check 2–4: validate chain contents
	diags, err := ValidateChain(chainPath)
	if err != nil {
		fmt.Printf("[FAIL] Chain read error: %v\n", err)
		return &HealthError{Code: ExitIOError, Message: err.Error()}
	}

	return reportDiagnostics(diags, chainPath)
}

func reportMissingChain(chainPath string) error {
	fmt.Println("[WARN] Chain file not found.")
	fmt.Println()
	fmt.Println("  To create the chain directory:")
	dir := filepath.Dir(chainPath)
	fmt.Printf("    mkdir -p %s\n", dir)
	fmt.Println()
	fmt.Println("  The chain will be created automatically on the next")
	fmt.Println("  successful 'evidencepack pack' run.")
	return nil // missing chain is a warn, not a failure
}

func reportDiagnostics(diags []ChainDiagnostic, chainPath string) error {
	if len(diags) == 0 {
		lineCount := countLines(chainPath)
		fmt.Printf("[OK]   Column count: all lines have %d columns\n", ChainCols)
		fmt.Println("[OK]   Entry hashes: all recomputed hashes match")
		fmt.Println("[OK]   Chain links: all prev_entry_sha256 values match")
		fmt.Printf("\nChain healthy: %d entries verified.\n", lineCount)
		return nil
	}

	// Report each diagnostic
	fails := 0
	warns := 0
	for _, d := range diags {
		prefix := "[FAIL]"
		if d.Severity == "WARN" {
			prefix = "[WARN]"
			warns++
		} else {
			fails++
		}
		if d.Line > 0 {
			fmt.Printf("%s Line %d: %s\n", prefix, d.Line, d.Message)
		} else {
			fmt.Printf("%s %s\n", prefix, d.Message)
		}
		if d.Fix != "" {
			fmt.Printf("  Fix: %s\n", d.Fix)
		}
	}

	fmt.Println()
	if fails > 0 {
		fmt.Printf("Chain INVALID: %d failure(s), %d warning(s)\n", fails, warns)
		fmt.Println()
		fmt.Println("Prevent: never edit chain manually; use 'evidencepack pack' only.")
		return &HealthError{Code: ExitTamper, Message: "chain validation failed"}
	}

	fmt.Printf("Chain warnings: %d warning(s)\n", warns)
	return nil
}

func countLines(path string) int {
	raw, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	lines := strings.Split(strings.TrimSpace(string(raw)), "\n")
	count := 0
	for _, l := range lines {
		if strings.TrimSpace(l) != "" {
			count++
		}
	}
	return count
}
