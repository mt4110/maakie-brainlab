package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadPolicy(t *testing.T) {
	tmpDir := t.TempDir()
	policyPath := filepath.Join(tmpDir, "policy.toml")
	content := `
version = 1
[keys]
allowed_key_ids = ["key1", "key2"]
[enforcement]
mode_local = "permissive"
mode_ci = "strict"
[signing]
require_signature_in_ci = true
enforce_allowlist_in_ci = true
[audit]
require_audit_in_ci = false
`
	if err := os.WriteFile(policyPath, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write policy file: %v", err)
	}

	p, err := LoadPolicy(policyPath)
	if err != nil {
		t.Fatalf("LoadPolicy failed: %v", err)
	}

	if p.Version != 1 {
		t.Errorf("expected version 1, got %d", p.Version)
	}
	if len(p.Keys.AllowedKeyIDs) != 2 {
		t.Errorf("expected 2 allowed keys, got %d", len(p.Keys.AllowedKeyIDs))
	}
	if p.Enforcement.ModeLocal != "permissive" {
		t.Errorf("expected mode_local permissive, got %s", p.Enforcement.ModeLocal)
	}
}

func TestEvaluatePolicy(t *testing.T) {
	p := &ReviewPackPolicy{
		Version: 1,
		Keys: KeysConfig{
			AllowedKeyIDs: []string{"key1"},
		},
		Enforcement: EnforcementConfig{
			ModeLocal: "permissive",
			ModeCI:    "strict",
		},
		Signing: SigningConfig{
			RequireSignatureInCI: true, // Test strict requirement
			EnforceAllowlistInCI: true,
		},
	}

	tests := []struct {
		name        string
		env         string
		hasSig      bool
		keyID       string
		expectError bool
	}{
		// Local (Permissive) - Violations should pass
		{"Local: No Signature", EnvLocal, false, "", false},
		{"Local: Bad Key", EnvLocal, true, "bad-key", false},

		// CI (Strict)
		{"CI: No Signature (Required)", EnvCI, false, "", true},
		{"CI: Bad Key (Enforced)", EnvCI, true, "bad-key", true},
		{"CI: Good Key", EnvCI, true, "key1", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := EvaluatePolicy(p, tt.env, tt.hasSig, tt.keyID)
			if tt.expectError && err == nil {
				t.Errorf("expected error, got nil")
			}
			if !tt.expectError && err != nil {
				t.Errorf("expected no error, got %v", err)
			}
		})
	}

	// Test case: CI strict but signature NOT required
	p.Signing.RequireSignatureInCI = false
	if err := EvaluatePolicy(p, EnvCI, false, ""); err != nil {
		t.Errorf("CI strict with no signature requirement should pass if signature missing, got error: %v", err)
	}
}

func TestDeterminePolicyEnv(t *testing.T) {
	// 1. CLI Preference
	if mode := DeterminePolicyEnv("ci"); mode != "ci" {
		t.Errorf("expected cli 'ci', got %s", mode)
	}

	// 2. Env Override
	os.Setenv(EnvPolicyMode, "local")
	defer os.Unsetenv(EnvPolicyMode)
	// Passing empty CLI should use Env
	if mode := DeterminePolicyEnv(""); mode != "local" {
		t.Errorf("expected env 'local', got %s", mode)
	}

	// 3. Auto (CI=true)
	os.Unsetenv(EnvPolicyMode)
	os.Setenv("CI", "true")
	defer os.Unsetenv("CI")
	if mode := DeterminePolicyEnv("auto"); mode != "ci" {
		t.Errorf("expected auto 'ci' (CI=true), got %s", mode)
	}
}
