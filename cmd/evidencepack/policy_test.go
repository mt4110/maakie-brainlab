package main

import (
	"crypto/ed25519"
	"crypto/sha256"
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
allowed_pubkey_sha256 = ["aabbcc"]
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
	if len(p.Keys.AllowedPubkeySHA256) != 1 {
		t.Errorf("expected 1 allowed fingerprint, got %d", len(p.Keys.AllowedPubkeySHA256))
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
			// Using empty fingerprint for legacy tests
			err := EvaluatePolicy(p, tt.env, tt.hasSig, tt.keyID, "")
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
	if err := EvaluatePolicy(p, EnvCI, false, "", ""); err != nil {
		t.Errorf("CI strict with no signature requirement should pass if signature missing, got error: %v", err)
	}
}

// TestEvaluatePolicyFingerprint tests Trust Anchor v1 fingerprint priority.
func TestEvaluatePolicyFingerprint(t *testing.T) {
	// Generate a deterministic key for testing
	seed := sha256.Sum256([]byte("reviewpack:keygen:v1:test-seed"))
	priv := ed25519.NewKeyFromSeed(seed[:])
	pub := priv.Public().(ed25519.PublicKey)
	fp := PubKeyFingerprint(pub)

	t.Run("Fingerprint priority: match", func(t *testing.T) {
		p := &ReviewPackPolicy{
			Version: 1,
			Keys: KeysConfig{
				AllowedPubkeySHA256: []string{fp},
				AllowedKeyIDs:       []string{"other-key"},
			},
			Enforcement: EnforcementConfig{ModeCI: "strict"},
			Signing:     SigningConfig{RequireSignatureInCI: true, EnforceAllowlistInCI: true},
		}
		if err := EvaluatePolicy(p, EnvCI, true, "any-keyid", fp); err != nil {
			t.Errorf("fingerprint match should pass: %v", err)
		}
	})

	t.Run("Fingerprint priority: mismatch", func(t *testing.T) {
		p := &ReviewPackPolicy{
			Version: 1,
			Keys: KeysConfig{
				AllowedPubkeySHA256: []string{"0000000000000000000000000000000000000000000000000000000000000000"},
				AllowedKeyIDs:       []string{"good-key"},
			},
			Enforcement: EnforcementConfig{ModeCI: "strict"},
			Signing:     SigningConfig{RequireSignatureInCI: true, EnforceAllowlistInCI: true},
		}
		// Even if keyid matches, fingerprint takes priority and should fail
		err := EvaluatePolicy(p, EnvCI, true, "good-key", fp)
		if err == nil {
			t.Error("fingerprint mismatch should fail even if keyid matches")
		}
	})

	t.Run("Fallback to keyid when no fingerprints", func(t *testing.T) {
		p := &ReviewPackPolicy{
			Version: 1,
			Keys: KeysConfig{
				AllowedPubkeySHA256: []string{},
				AllowedKeyIDs:       []string{"my-key"},
			},
			Enforcement: EnforcementConfig{ModeCI: "strict"},
			Signing:     SigningConfig{RequireSignatureInCI: true, EnforceAllowlistInCI: true},
		}
		if err := EvaluatePolicy(p, EnvCI, true, "my-key", fp); err != nil {
			t.Errorf("keyid fallback should pass: %v", err)
		}
		err := EvaluatePolicy(p, EnvCI, true, "wrong-key", fp)
		if err == nil {
			t.Error("keyid fallback should reject wrong key")
		}
	})

	t.Run("Both empty: FAIL", func(t *testing.T) {
		p := &ReviewPackPolicy{
			Version: 1,
			Keys: KeysConfig{
				AllowedPubkeySHA256: []string{},
				AllowedKeyIDs:       []string{},
			},
			Enforcement: EnforcementConfig{ModeCI: "strict"},
			Signing:     SigningConfig{RequireSignatureInCI: true, EnforceAllowlistInCI: true},
		}
		err := EvaluatePolicy(p, EnvCI, true, "any-key", fp)
		if err == nil {
			t.Error("both empty should fail")
		}
	})
}

// TestSeedDeterminism verifies that --seed produces the same key/fingerprint.
func TestSeedDeterminism(t *testing.T) {
	domain := "reviewpack:keygen:v1:"
	seed := "test-determinism"

	h1 := sha256.Sum256([]byte(domain + seed))
	priv1 := ed25519.NewKeyFromSeed(h1[:])
	pub1 := priv1.Public().(ed25519.PublicKey)
	fp1 := PubKeyFingerprint(pub1)

	h2 := sha256.Sum256([]byte(domain + seed))
	priv2 := ed25519.NewKeyFromSeed(h2[:])
	pub2 := priv2.Public().(ed25519.PublicKey)
	fp2 := PubKeyFingerprint(pub2)

	if fp1 != fp2 {
		t.Errorf("same seed should produce same fingerprint: %s vs %s", fp1, fp2)
	}

	// Different seed should produce different fingerprint
	h3 := sha256.Sum256([]byte(domain + "different-seed"))
	priv3 := ed25519.NewKeyFromSeed(h3[:])
	pub3 := priv3.Public().(ed25519.PublicKey)
	fp3 := PubKeyFingerprint(pub3)

	if fp1 == fp3 {
		t.Error("different seeds should produce different fingerprints")
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
