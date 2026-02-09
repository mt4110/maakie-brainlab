package main

import (
	"bytes"
	"fmt"
	"os"

	"golang.org/x/crypto/openpgp"
	"golang.org/x/crypto/openpgp/armor"
)

// signFile creates a detached armored signature for the target file using the private key at privKeyPath.
// It creates <targetPath>.asc
func signFile(privKeyPath, targetPath string) error {
	// Read Private Key
	keyBytes, err := os.ReadFile(privKeyPath)
	if err != nil {
		return fmt.Errorf("read key: %w", err)
	}
	
	block, err := armor.Decode(bytes.NewReader(keyBytes))
	if err != nil {
		return fmt.Errorf("decode armor: %w", err)
	}
	if block.Type != openpgp.PrivateKeyType {
		return fmt.Errorf("invalid key type: %s", block.Type)
	}

	entityList, err := openpgp.ReadKeyRing(block.Body)
	if err != nil {
		return fmt.Errorf("read keyring: %w", err)
	}
	signer := entityList[0]

	// Read Target
	targetBytes, err := os.ReadFile(targetPath)
	if err != nil {
		return fmt.Errorf("read target: %w", err)
	}

	// Create Signature
	sigBuf := new(bytes.Buffer)
	if err := openpgp.ArmoredDetachSign(sigBuf, signer, bytes.NewReader(targetBytes), nil); err != nil {
		return fmt.Errorf("signing: %w", err)
	}

	outPath := targetPath + ".asc"
	if err := os.WriteFile(outPath, sigBuf.Bytes(), 0644); err != nil {
		return fmt.Errorf("write sig: %w", err)
	}
	fmt.Printf("[Sign] Signed %s -> %s\n", targetPath, outPath)
	return nil
}
