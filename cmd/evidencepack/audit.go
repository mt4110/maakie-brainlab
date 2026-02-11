package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// Audit Chain v1 Constants
const (
	AuditVersion = "1"
	AuditLogDir  = ".local/reviewpack_audit"
	AuditLogFile = "audit.log.jsonl"
	// GenesisHash is the prev_hash for the first entry (64 zero chars).
	GenesisHash = "0000000000000000000000000000000000000000000000000000000000000000"
)

// AuditEntry represents a single audit log entry.
// Field order is canonical: hash computation depends on this order.
type AuditEntry struct {
	EventType      string `json:"event_type"`
	Result         string `json:"result"`
	ArtifactPath   string `json:"artifact_path"`
	ArtifactSHA256 string `json:"artifact_sha256"`
	SigPath        string `json:"sig_path,omitempty"`
	KeyID          string `json:"key_id,omitempty"`
	GitSHA         string `json:"git_sha,omitempty"`
	ToolVersion    string `json:"tool_version,omitempty"`
	UTCTimestamp   string `json:"utc_ts"`
	PrevHash       string `json:"prev_hash"`
	EntryHash      string `json:"entry_hash"`
}

// auditCanonical is a shadow struct with identical fields and tags,
// but entry_hash is always emitted (never omitted) and set to "" for hashing.
type auditCanonical struct {
	EventType      string `json:"event_type"`
	Result         string `json:"result"`
	ArtifactPath   string `json:"artifact_path"`
	ArtifactSHA256 string `json:"artifact_sha256"`
	SigPath        string `json:"sig_path,omitempty"`
	KeyID          string `json:"key_id,omitempty"`
	GitSHA         string `json:"git_sha,omitempty"`
	ToolVersion    string `json:"tool_version,omitempty"`
	UTCTimestamp   string `json:"utc_ts"`
	PrevHash       string `json:"prev_hash"`
	EntryHash      string `json:"entry_hash"`
}

// CanonicalAuditJSON returns deterministic JSON for hash computation.
// entry_hash is set to "" so it is excluded from the hash input.
func CanonicalAuditJSON(e *AuditEntry) ([]byte, error) {
	c := auditCanonical{
		EventType:      e.EventType,
		Result:         e.Result,
		ArtifactPath:   e.ArtifactPath,
		ArtifactSHA256: e.ArtifactSHA256,
		SigPath:        e.SigPath,
		KeyID:          e.KeyID,
		GitSHA:         e.GitSHA,
		ToolVersion:    e.ToolVersion,
		UTCTimestamp:   e.UTCTimestamp,
		PrevHash:       e.PrevHash,
		EntryHash:      "", // always empty for hashing
	}
	return json.Marshal(c)
}

// ComputeAuditEntryHash computes sha256(prevHash + "\n" + canonicalJSON).
func ComputeAuditEntryHash(prevHash string, canonicalJSON []byte) string {
	input := prevHash + "\n" + string(canonicalJSON)
	sum := sha256.Sum256([]byte(input))
	return hex.EncodeToString(sum[:])
}

// ---------------------------------------------------------------------------
// Logger (write side)
// ---------------------------------------------------------------------------

// AuditLogger handles append-only audit logging with hash chain.
type AuditLogger struct {
	path string
	mu   sync.Mutex
}

// NewAuditLogger initializes the logger.
func NewAuditLogger(repoRoot string) (*AuditLogger, error) {
	dir := filepath.Join(repoRoot, AuditLogDir)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create audit dir: %w", err)
	}
	return &AuditLogger{
		path: filepath.Join(dir, AuditLogFile),
	}, nil
}

// LogEvent writes a new entry with hash chain.
func (l *AuditLogger) LogEvent(event *AuditEntry) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	// 1. Get prev hash
	prevHash, err := l.getLastHash()
	if err != nil {
		return err
	}
	event.PrevHash = prevHash

	// 2. Compute entry hash using canonical JSON
	canonical, err := CanonicalAuditJSON(event)
	if err != nil {
		return fmt.Errorf("failed to compute canonical JSON: %w", err)
	}
	event.EntryHash = ComputeAuditEntryHash(prevHash, canonical)

	// 3. Write final JSON line
	finalBytes, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal audit entry: %w", err)
	}

	f, err := os.OpenFile(l.path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open audit log: %w", err)
	}
	defer f.Close()

	if _, err := f.Write(finalBytes); err != nil {
		return err
	}
	if _, err := f.WriteString("\n"); err != nil {
		return err
	}
	return nil
}

func (l *AuditLogger) getLastHash() (string, error) {
	f, err := os.Open(l.path)
	if os.IsNotExist(err) {
		return GenesisHash, nil
	}
	if err != nil {
		return "", err
	}
	defer f.Close()

	stat, err := f.Stat()
	if err != nil {
		return "", err
	}
	if stat.Size() == 0 {
		return GenesisHash, nil
	}

	// Scan all entries to find the last entry_hash
	var lastEntry AuditEntry
	decoder := json.NewDecoder(f)
	found := false
	for decoder.More() {
		if err := decoder.Decode(&lastEntry); err != nil {
			return "", fmt.Errorf("corrupt audit log: %w", err)
		}
		found = true
	}

	if !found {
		return GenesisHash, nil
	}
	return lastEntry.EntryHash, nil
}

// runAudit is kept for backward compatibility.
// v1: audit is an alias of health.
func runAudit(args []string) error {
	return runHealth(args)
}
