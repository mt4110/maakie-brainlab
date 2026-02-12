package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/BurntSushi/toml"
)

// Policy Modes and Environments
const (
	EnvLocal = "local"
	EnvCI    = "ci"

	ModePermissive = "permissive"
	ModeStrict     = "strict"

	// Env var for policy mode override
	EnvPolicyMode = "REVIEWPACK_POLICY_MODE"
)

// ReviewPackPolicy represents ops/reviewpack_policy.toml structure
type ReviewPackPolicy struct {
	Version     int               `toml:"version"`
	Keys        KeysConfig        `toml:"keys"`
	Enforcement EnforcementConfig `toml:"enforcement"`
	Signing     SigningConfig     `toml:"signing"`
	Audit       AuditConfig       `toml:"audit"`
}

type KeysConfig struct {
	AllowedKeyIDs       []string `toml:"allowed_key_ids"`
	AllowedPubkeySHA256 []string `toml:"allowed_pubkey_sha256"`
}

type EnforcementConfig struct {
	ModeLocal string `toml:"mode_local"`
	ModeCI    string `toml:"mode_ci"`
}

type SigningConfig struct {
	RequireSignatureInCI bool `toml:"require_signature_in_ci"`
	EnforceAllowlistInCI bool `toml:"enforce_allowlist_in_ci"`
}

type AuditConfig struct {
	RequireAuditInCI bool `toml:"require_audit_in_ci"`
}

// LoadPolicy parses TOML from path
func LoadPolicy(path string) (*ReviewPackPolicy, error) {
	var p ReviewPackPolicy
	if _, err := toml.DecodeFile(path, &p); err != nil {
		return nil, fmt.Errorf("failed to decode policy file %s: %w", path, err)
	}
	if p.Version != 1 {
		return nil, fmt.Errorf("unsupported policy version %d (expected 1)", p.Version)
	}
	return &p, nil
}

// DeterminePolicyEnv resolves the active environment (cli > env > auto -> local/ci)
func DeterminePolicyEnv(cliEnv string) string {
	if cliEnv != "" && cliEnv != "auto" {
		return cliEnv
	}
	envVal := os.Getenv(EnvPolicyMode)
	if envVal != "" && envVal != "auto" {
		return envVal
	}
	if os.Getenv("CI") == "true" || os.Getenv("GITHUB_ACTIONS") == "true" {
		return EnvCI
	}
	return EnvLocal
}

// EvaluatePolicy checks if the current state satisfies the policy.
// pubKeySHA256 is the SHA256 fingerprint of the signer's public key (Trust Anchor v1).
func EvaluatePolicy(p *ReviewPackPolicy, env string, hasSignature bool, keyID string, pubKeySHA256 string) error {
	applicationMode := resolveApplicationMode(p, env)
	if applicationMode == ModePermissive {
		return nil
	}

	// Strict Enforcement
	if !hasSignature {
		if env == EnvCI && p.Signing.RequireSignatureInCI {
			return fmt.Errorf("policy violation: signature required in CI but not found")
		}
		return nil
	}

	return checkKeyAllowlist(p, env, keyID, pubKeySHA256)
}

func resolveApplicationMode(p *ReviewPackPolicy, env string) string {
	if env == EnvCI {
		return p.Enforcement.ModeCI
	}
	return p.Enforcement.ModeLocal
}

// checkKeyAllowlist enforces Trust Anchor v1 priority:
// 1. allowed_pubkey_sha256 non-empty → fingerprint enforce (priority)
// 2. allowed_pubkey_sha256 empty → allowed_key_ids fallback (compat)
// 3. Both empty → FAIL (misconfiguration)
func checkKeyAllowlist(p *ReviewPackPolicy, env string, keyID string, pubKeySHA256 string) error {
	if env != EnvCI || !p.Signing.EnforceAllowlistInCI {
		return nil
	}

	hasFP := len(p.Keys.AllowedPubkeySHA256) > 0
	hasKID := len(p.Keys.AllowedKeyIDs) > 0

	// Priority 1: fingerprint allowlist
	if hasFP {
		for _, allowed := range p.Keys.AllowedPubkeySHA256 {
			if strings.EqualFold(allowed, pubKeySHA256) {
				return nil
			}
		}
		return fmt.Errorf("policy violation: signer pubkey is not allowed (Trust Anchor v1)\n"+
			"  Expected PubKeySHA256: %v\n"+
			"  Got PubKeySHA256:      %s\n"+
			"  Policy: ops/reviewpack_policy.toml (keys.allowed_pubkey_sha256)\n"+
			"  Regen (binary): evidencepack keygen --id <id> --seed \"reviewpack-smoke-v1\"\n"+
			"  Regen (go run): go run ./cmd/evidencepack keygen --id <id> --seed \"reviewpack-smoke-v1\"\n"+
			"  Note: KeyID is a label; allowlist is enforced by PubKeySHA256",
			p.Keys.AllowedPubkeySHA256, pubKeySHA256)
	}

	// Priority 2: keyid fallback
	if hasKID {
		for _, allowedID := range p.Keys.AllowedKeyIDs {
			if allowedID == keyID {
				return nil
			}
		}
		return fmt.Errorf("policy violation: key %s is not in allowed_key_ids (see ops/reviewpack_policy.toml)", keyID)
	}

	// Priority 3: both empty → FAIL
	return fmt.Errorf("policy violation: no allowlist configured (both allowed_pubkey_sha256 and allowed_key_ids are empty)")
}
