package main

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
)

func TestAuditLog_HashChain(t *testing.T) {
	tmpDir := t.TempDir()

	// Initialize Logger
	logger, err := NewAuditLogger(tmpDir)
	if err != nil {
		t.Fatalf("Failed to init logger: %v", err)
	}

	// Create fake events
	e1 := &AuditEntry{EventType: "test", Result: "ok", ArtifactSHA256: "aaa", UTCTimestamp: "2024-01-01T00:00:00Z"}
	if err := logger.LogEvent(e1); err != nil {
		t.Fatalf("LogEvent 1 failed: %v", err)
	}

	e2 := &AuditEntry{EventType: "test", Result: "fail", ArtifactSHA256: "bbb", UTCTimestamp: "2024-01-01T00:00:01Z"}
	if err := logger.LogEvent(e2); err != nil {
		t.Fatalf("LogEvent 2 failed: %v", err)
	}

	// Verify File Content
	content, err := os.ReadFile(logger.path)
	if err != nil {
		t.Fatalf("Failed to read log file: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(content)), "\n")
	if len(lines) != 2 {
		t.Fatalf("Expected 2 lines, got %d", len(lines))
	}

	var entry1, entry2 AuditEntry
	json.Unmarshal([]byte(lines[0]), &entry1)
	json.Unmarshal([]byte(lines[1]), &entry2)

	// Check Genesis
	if entry1.PrevHash != GenesisHash {
		t.Errorf("Entry1 PrevHash expected %s, got %s", GenesisHash, entry1.PrevHash)
	}
	if entry1.EntryHash == "" {
		t.Error("Entry1 EntryHash is empty")
	}

	// Check Chain
	if entry2.PrevHash != entry1.EntryHash {
		t.Errorf("Chain broken: Entry2.PrevHash %s != Entry1.EntryHash %s", entry2.PrevHash, entry1.EntryHash)
	}
}
