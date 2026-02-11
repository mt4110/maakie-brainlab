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

// Audit Constants
const (
	AuditLogDir  = ".local/reviewpack_audit"
	AuditLogFile = "audit.log.jsonl"
	GenesisHash  = "GENESIS"
)

// AuditEntry represents a single log entry
type AuditEntry struct {
	EventType      string `json:"event_type"` // "sign", "verify"
	Result         string `json:"result"`     // "ok", "fail"
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

// AuditLogger handles secure logging
type AuditLogger struct {
	path string
	mu   sync.Mutex
}

// NewAuditLogger initializes the logger
func NewAuditLogger(repoRoot string) (*AuditLogger, error) {
	dir := filepath.Join(repoRoot, AuditLogDir)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create audit dir: %w", err)
	}
	return &AuditLogger{
		path: filepath.Join(dir, AuditLogFile),
	}, nil
}

// LogEvent writes a new entry with hash chain
func (l *AuditLogger) LogEvent(event *AuditEntry) error {
	l.mu.Lock()
	defer l.mu.Unlock()

	// 1. Read last line to get PrevHash
	prevHash, err := l.getLastHash()
	if err != nil {
		return err
	}
	event.PrevHash = prevHash

	// 2. Compute EntryHash
	// entry_hash = sha256(prev_hash + "\n" + json_without_entry_hash)
	// We construct a temporary struct or just marshal without EntryHash?
	// Struct has EntryHash field. If we leave it empty, it marshals to ""?
	// The requirement is "json_bytes_without_entry_hash".
	// Let's marshal with EntryHash="" first.
	event.EntryHash = ""

	// Canonical JSON? "structで順序固定" (Go default for struct is fixed field order?)
	// Go's json.Marshal sorts map keys, but struct fields are serialized in definition order?
	// Actually struct fields are usually serialized in definition order in standard encoding/json?
	// No, checking... "The default encoding for struct fields is the order they are defined".
	// Yes. But let's verify if we need strict canonicalization (e.g. JCS).
	// Requirement say "Canonical JSON はキー順固定（実装側で固定順序で出力）".
	// Since we use a struct, and standard Go `json` package emits fields in order of definition (mostly),
	// we should be okay as long as we don't change the struct.

	jsonBytes, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal audit entry: %w", err)
	}

	// Calculate Hash
	hashInput := prevHash + "\n" + string(jsonBytes)
	sum := sha256.Sum256([]byte(hashInput))
	event.EntryHash = hex.EncodeToString(sum[:])

	// 3. Write strict JSON line
	finalBytes, err := json.Marshal(event)
	if err != nil {
		return err
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
	// Read file to find last line.
	// Efficiently read from end? For now, just read all is safest simple impl, or seek end.
	f, err := os.Open(l.path)
	if os.IsNotExist(err) {
		return GenesisHash, nil
	}
	if err != nil {
		return "", err
	}
	defer f.Close()

	// Seek to end and scan backwards? Or just read strict lines.
	// Since we need to be robust, let's read the file.
	// If file is huge, this is slow. But for S7 it's fine.
	// Optimization: valid JSONL, so we can seek backwards for last newline.

	stat, err := f.Stat()
	if err != nil { return "", err }
	if stat.Size() == 0 {
		return GenesisHash, nil
	}

	// Simple backward scanning
	buf := make([]byte, 1024)
	start := stat.Size()

	for {
		offset := int64(0)
		if start > 1024 {
			offset = start - 1024
		}

		_, err := f.ReadAt(buf[:start-offset], offset)
		if err != nil { return "", err }

		// Look for last newline
		// Caution: file ends with newline. We need the line BEFORE that.
		// If we read the last block, it likely ends with \n.

		// Let's just use a scanner for simplicity in V1 for now creates cleaner code
		// if performance hits, we optimize.
		break
	}

	// Re-open for scanner
	f.Seek(0, 0)
	var lastEntry AuditEntry
	decoder := json.NewDecoder(f)
	found := false
	for decoder.More() {
		if err := decoder.Decode(&lastEntry); err != nil {
			// If we encounter garbage, what to do? Fail safe.
			return "", fmt.Errorf("corrupt audit log: %w", err)
		}
		found = true
	}

	if !found {
		return GenesisHash, nil
	}
	return lastEntry.EntryHash, nil
}
