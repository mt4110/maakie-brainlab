package main

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// ---------------------------------------------------------------------------
// Audit Chain v1 — TSV format
// ---------------------------------------------------------------------------

const (
	ChainVersion = "1"
	ChainDir     = ".local/reviewpack_artifacts"
	ChainFile    = "AUDIT_CHAIN_v1.tsv"
	ChainCols    = 10
	// ChainGenesisHash is the prev_entry_sha256 for the very first entry.
	ChainGenesisHash = "0000000000000000000000000000000000000000000000000000000000000000"
)

// ChainEntry represents one line (row) in the TSV audit chain.
// Column order is fixed and canonical — hash computation depends on it.
type ChainEntry struct {
	Version         string // col 1: always "1"
	TimestampUTC    string // col 2: e.g. 20260211T161122Z
	PackName        string // col 3: e.g. review_bundle_20260211_161122.tar.gz
	PackSHA256      string // col 4: hex 64
	ManifestSHA256  string // col 5: MANIFEST.tsv sha inside bundle
	ChecksumsSHA256 string // col 6: CHECKSUMS.sha256 sha inside bundle
	GitHead         string // col 7: HEAD at generation time
	ToolVersion     string // col 8: tool version (or "dev")
	PrevEntrySHA256 string // col 9: previous line's entry_sha256
	EntrySHA256     string // col 10: sha256 of cols 1–9 tab-joined
}

// ---------------------------------------------------------------------------
// Parse / Format
// ---------------------------------------------------------------------------

// ParseChainEntry splits a TSV line into a ChainEntry.
func ParseChainEntry(line string) (*ChainEntry, error) {
	cols := strings.Split(line, "\t")
	if len(cols) != ChainCols {
		return nil, fmt.Errorf("expected %d columns, got %d", ChainCols, len(cols))
	}
	return &ChainEntry{
		Version:         cols[0],
		TimestampUTC:    cols[1],
		PackName:        cols[2],
		PackSHA256:      cols[3],
		ManifestSHA256:  cols[4],
		ChecksumsSHA256: cols[5],
		GitHead:         cols[6],
		ToolVersion:     cols[7],
		PrevEntrySHA256: cols[8],
		EntrySHA256:     cols[9],
	}, nil
}

// FormatChainEntry serializes a ChainEntry to a single TSV line (no trailing newline).
func FormatChainEntry(e *ChainEntry) string {
	return strings.Join([]string{
		e.Version,
		e.TimestampUTC,
		e.PackName,
		e.PackSHA256,
		e.ManifestSHA256,
		e.ChecksumsSHA256,
		e.GitHead,
		e.ToolVersion,
		e.PrevEntrySHA256,
		e.EntrySHA256,
	}, "\t")
}

// ---------------------------------------------------------------------------
// Hash computation
// ---------------------------------------------------------------------------

// ComputeChainEntryHash computes sha256 of columns 1–9 tab-joined.
// No trailing newline in the hash input.
func ComputeChainEntryHash(e *ChainEntry) string {
	payload := strings.Join([]string{
		e.Version,
		e.TimestampUTC,
		e.PackName,
		e.PackSHA256,
		e.ManifestSHA256,
		e.ChecksumsSHA256,
		e.GitHead,
		e.ToolVersion,
		e.PrevEntrySHA256,
	}, "\t")
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:])
}

// ---------------------------------------------------------------------------
// Append
// ---------------------------------------------------------------------------

// ChainWriter handles append-only writes to the TSV chain file.
type ChainWriter struct {
	path string
	mu   sync.Mutex
}

// NewChainWriter creates a ChainWriter, ensuring the directory exists.
func NewChainWriter(repoRoot string) (*ChainWriter, error) {
	dir := filepath.Join(repoRoot, ChainDir)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create chain dir: %w", err)
	}
	return &ChainWriter{
		path: filepath.Join(dir, ChainFile),
	}, nil
}

// Append writes a new chain entry. It reads the last entry to get prev_hash,
// sets Version, PrevEntrySHA256, and EntrySHA256 automatically.
// The caller must fill: TimestampUTC, PackName, PackSHA256, ManifestSHA256,
// ChecksumsSHA256, GitHead, ToolVersion.
func (w *ChainWriter) Append(e *ChainEntry) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	prevHash, err := readLastEntryHash(w.path)
	if err != nil {
		return fmt.Errorf("failed to read last chain entry: %w", err)
	}

	e.Version = ChainVersion
	e.PrevEntrySHA256 = prevHash
	e.EntrySHA256 = ComputeChainEntryHash(e)

	line := FormatChainEntry(e)

	f, err := os.OpenFile(w.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open chain file: %w", err)
	}
	defer f.Close()

	if _, err := f.WriteString(line + "\n"); err != nil {
		return fmt.Errorf("failed to write chain entry: %w", err)
	}
	return nil
}

// readLastEntryHash returns the entry_sha256 of the last line, or genesis hash.
func readLastEntryHash(path string) (string, error) {
	f, err := os.Open(path)
	if os.IsNotExist(err) {
		return ChainGenesisHash, nil
	}
	if err != nil {
		return "", err
	}
	defer f.Close()

	var lastLine string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			lastLine = line
		}
	}
	if err := scanner.Err(); err != nil {
		return "", err
	}
	if lastLine == "" {
		return ChainGenesisHash, nil
	}

	entry, err := ParseChainEntry(lastLine)
	if err != nil {
		return "", fmt.Errorf("corrupt last chain entry: %w", err)
	}
	return entry.EntrySHA256, nil
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

// ChainDiagnostic represents one diagnostic finding from chain validation.
type ChainDiagnostic struct {
	Line     int    // 1-indexed
	Severity string // "FAIL" or "WARN"
	Message  string
	Fix      string // suggested fix
}

// ValidateChain checks the full chain file and returns all diagnostics.
// Returns nil slice + nil error if chain is healthy.
func ValidateChain(path string) ([]ChainDiagnostic, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("failed to open chain file: %w", err)
	}
	defer f.Close()

	var diags []ChainDiagnostic
	scanner := bufio.NewScanner(f)
	lineNum := 0
	prevHash := ChainGenesisHash

	for scanner.Scan() {
		lineNum++
		line := strings.TrimRight(scanner.Text(), "\r")
		if line == "" {
			continue
		}

		entryDiags := validateChainLine(line, lineNum, prevHash)
		diags = append(diags, entryDiags...)

		if len(entryDiags) > 0 {
			// Still try to continue for maximum diagnostics.
			// Use the claimed entry hash as prev for next line.
			entry, parseErr := ParseChainEntry(line)
			if parseErr == nil {
				prevHash = entry.EntrySHA256
			}
			continue
		}

		entry, _ := ParseChainEntry(line)
		prevHash = entry.EntrySHA256
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("failed to read chain file: %w", err)
	}

	if lineNum == 0 {
		diags = append(diags, ChainDiagnostic{
			Line: 0, Severity: "WARN", Message: "chain file is empty",
			Fix: "Run 'evidencepack pack' to create the first entry.",
		})
	}

	return diags, nil
}

// validateChainLine validates a single TSV line and returns any diagnostics.
func validateChainLine(line string, lineNum int, expectedPrev string) []ChainDiagnostic {
	var diags []ChainDiagnostic

	entry, err := ParseChainEntry(line)
	if err != nil {
		diags = append(diags, ChainDiagnostic{
			Line: lineNum, Severity: "FAIL",
			Message: fmt.Sprintf("invalid TSV: %v", err),
			Fix:     "Restore from backup or truncate to last valid line.",
		})
		return diags
	}

	if entry.Version != ChainVersion {
		diags = append(diags, ChainDiagnostic{
			Line: lineNum, Severity: "FAIL",
			Message: fmt.Sprintf("unsupported version: %q (expected %q)", entry.Version, ChainVersion),
			Fix:     "This tool only supports chain version 1.",
		})
	}

	if entry.PrevEntrySHA256 != expectedPrev {
		diags = append(diags, ChainDiagnostic{
			Line: lineNum, Severity: "FAIL",
			Message: fmt.Sprintf("prev_entry_sha256 mismatch: expected %s, got %s",
				expectedPrev, entry.PrevEntrySHA256),
			Fix: "Chain link broken. Restore from backup or truncate to last valid line.",
		})
	}

	expectedHash := ComputeChainEntryHash(entry)
	if entry.EntrySHA256 != expectedHash {
		diags = append(diags, ChainDiagnostic{
			Line: lineNum, Severity: "FAIL",
			Message: fmt.Sprintf("entry_sha256 mismatch: expected %s, got %s",
				expectedHash, entry.EntrySHA256),
			Fix: "Entry content was modified. Restore from backup.",
		})
	}

	return diags
}
