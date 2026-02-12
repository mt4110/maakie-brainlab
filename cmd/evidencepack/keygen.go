package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

const CmdKeygen = "keygen"

func runKeygen(args []string) error {
	fs := flag.NewFlagSet("keygen", flag.ExitOnError)
	keyID := fs.String("id", "", "Key identifier (required)")
	outDir := fs.String("out-dir", ".", "Output directory for key files")
	seed := fs.String("seed", "", "Deterministic seed string (same seed = same key)")
	if err := fs.Parse(args); err != nil {
		return err
	}

	if *keyID == "" {
		return fmt.Errorf("--id is required")
	}

	var pub ed25519.PublicKey
	var priv ed25519.PrivateKey

	if *seed != "" {
		// Deterministic: sha256("reviewpack:keygen:v1:" + seed) → 32-byte Ed25519 seed
		domain := "reviewpack:keygen:v1:"
		h := sha256.Sum256([]byte(domain + *seed))
		priv = ed25519.NewKeyFromSeed(h[:])
		pub = priv.Public().(ed25519.PublicKey)
	} else {
		// Random
		var err error
		pub, priv, err = ed25519.GenerateKey(rand.Reader)
		if err != nil {
			return fmt.Errorf("keygen failed: %w", err)
		}
	}

	if err := os.MkdirAll(*outDir, 0755); err != nil {
		return fmt.Errorf("failed to create output dir: %w", err)
	}

	// Write private key (base64, restrictive perms)
	privB64 := base64.StdEncoding.EncodeToString(priv)
	privPath := filepath.Join(*outDir, *keyID+".key")
	if err := os.WriteFile(privPath, []byte(privB64+"\n"), 0600); err != nil {
		return fmt.Errorf("failed to write private key: %w", err)
	}

	// Write public key (JSON CryptoKey format)
	pubJSON, err := ExportPublicKeyJSON(pub, *keyID)
	if err != nil {
		return fmt.Errorf("failed to export public key: %w", err)
	}
	pubJSON = append(pubJSON, '\n')
	pubPath := filepath.Join(*outDir, *keyID+".pub")
	if err := os.WriteFile(pubPath, pubJSON, 0644); err != nil {
		return fmt.Errorf("failed to write public key: %w", err)
	}

	fingerprint := PubKeyFingerprint(pub)
	fmt.Printf("Generated keypair:\n  Private: %s\n  Public:  %s\n  PubKeySHA256: %s\n", privPath, pubPath, fingerprint)
	return nil
}
