package main

import (
	"fmt"
	"os"

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
	AllowedKeyIDs []string `toml:"allowed_key_ids"`
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
// This strictly returns "local" or "ci", which then maps to strict/permissive via policy.
func DeterminePolicyEnv(cliEnv string) string {
	// 1. CLI explicit
	if cliEnv != "" && cliEnv != "auto" {
		return cliEnv
	}

	// 2. Env explicit
	envVal := os.Getenv(EnvPolicyMode)
	if envVal != "" && envVal != "auto" {
		return envVal
	}

	// 3. Auto detection
	// If CI=true or GITHUB_ACTIONS=true -> ci
	if os.Getenv("CI") == "true" || os.Getenv("GITHUB_ACTIONS") == "true" {
		return EnvCI
	}
	return EnvLocal
}

// EvaluatePolicy checks if the current state satisfies the policy for the given environment.
// env should be "local" or "ci" (resolved by DeterminePolicyEnv).
// returns error ONLY if violation found in a STRICT context.
func EvaluatePolicy(p *ReviewPackPolicy, env string, hasSignature bool, keyID string) error {
	// 1. Determine enforcement application (strict vs permissive)
	applicationMode := ModePermissive
	if env == EnvCI {
		applicationMode = p.Enforcement.ModeCI
	} else {
		applicationMode = p.Enforcement.ModeLocal
	}

	// If permissive, we do not return verification errors for policy violations.
	if applicationMode == ModePermissive {
		return nil
	}

	// Strict Enforcement Logic

	// 2. Check Signature Requirement
	if !hasSignature {
		if env == EnvCI && p.Signing.RequireSignatureInCI {
			return fmt.Errorf("policy violation: signature required in CI but not found")
		}
		// If signature not required, allow it.
		return nil
	}

	// 3. Check Allowlist (if signature present)
	if hasSignature {
		// Only enforce allowlist if configured for this environment (CI)
		// Logic: if env is CI, check EnforceAllowlistInCI
		shouldEnforce := false
		if env == EnvCI {
			shouldEnforce = p.Signing.EnforceAllowlistInCI
		}

		if shouldEnforce {
			allowed := false
			for _, allowedID := range p.Keys.AllowedKeyIDs {
				if allowedID == keyID {
					allowed = true
					break
				}
			}
			if !allowed {
				return fmt.Errorf("policy violation: key %s is not in allowed_key_ids (see ops/reviewpack_policy.toml)", keyID)
			}
		}
	}

	return nil
}
