package main

import (
	"bytes"
	"flag"
	"fmt"
	"log"
	"os"

	"golang.org/x/crypto/openpgp"
	"golang.org/x/crypto/openpgp/armor"
)

func main() {
	mode := flag.String("mode", "", "keygen, sign, or verify")
	keyFile := flag.String("key", "", "Private key for signing, Public key for verifying")
	target := flag.String("target", "", "Target file to sign/verify")
	sigFile := flag.String("sig", "", "Signature file for verification (optional for sign, defaults to target.asc)")
	identity := flag.String("id", "S6 Builder <builder@s6.ops>", "Identity name for keygen")

	flag.Parse()

	if *mode == "" {
		log.Fatal("Usage: gopsign -mode=[keygen|sign|verify] ...")
	}

	switch *mode {
	case "keygen":
		if err := generateKeys(*identity); err != nil {
			log.Fatalf("Keygen failed: %v", err)
		}
	case "sign":
		if *keyFile == "" || *target == "" {
			log.Fatal("Usage: gopsign -mode=sign -key=priv.asc -target=file")
		}
		if err := signFile(*keyFile, *target); err != nil {
			log.Fatalf("Signing failed: %v", err)
		}
	case "verify":
		if *keyFile == "" || *target == "" {
			log.Fatal("Usage: gopsign -mode=verify -key=pub.asc -target=file [-sig=file.asc]")
		}
		if err := verifyFile(*keyFile, *target, *sigFile); err != nil {
			log.Fatalf("Verification failed: %v", err)
		}
	default:
		log.Fatalf("Unknown mode: %s", *mode)
	}
}

func generateKeys(name string) error {
	const bitLength = 2048 // RSA 2048 for compatibility/speed

	// Generate Key
	key, err := openpgp.NewEntity(name, "S6 Generated Key", "", nil)
	if err != nil {
		return err
	}

	// Serialize Private Key
	privHeader := make(map[string]string)
	privHeader["Version"] = "S6 GoSign 1.0"
	
	privBuf := new(bytes.Buffer)
	wPriv, err := armor.Encode(privBuf, openpgp.PrivateKeyType, privHeader)
	if err != nil {
		return err
	}
	if err := key.SerializePrivate(wPriv, nil); err != nil {
		return err
	}
	wPriv.Close()
	if err := os.WriteFile("privkey.asc", privBuf.Bytes(), 0600); err != nil {
		return err
	}
	fmt.Println("Generated privkey.asc")

	// Serialize Public Key
	pubHeader := make(map[string]string)
	pubHeader["Version"] = "S6 GoSign 1.0"

	pubBuf := new(bytes.Buffer)
	wPub, err := armor.Encode(pubBuf, openpgp.PublicKeyType, pubHeader)
	if err != nil {
		return err
	}
	if err := key.Serialize(wPub); err != nil {
		return err
	}
	wPub.Close()
	if err := os.WriteFile("pubkey.asc", pubBuf.Bytes(), 0644); err != nil {
		return err
	}
	fmt.Println("Generated pubkey.asc")
	return nil
}

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
	fmt.Printf("Signed %s -> %s\n", targetPath, outPath)
	return nil
}

func verifyFile(pubKeyPath, targetPath, sigPath string) error {
	if sigPath == "" {
		sigPath = targetPath + ".asc"
	}

	// Read Public Key
	keyBytes, err := os.ReadFile(pubKeyPath)
	if err != nil {
		return fmt.Errorf("read key: %w", err)
	}
	block, err := armor.Decode(bytes.NewReader(keyBytes))
	if err != nil {
		return fmt.Errorf("decode armor: %w", err)
	}
	keyRing, err := openpgp.ReadKeyRing(block.Body)
	if err != nil {
		return fmt.Errorf("read keyring: %w", err)
	}

	// Read Target
	targetBytes, err := os.ReadFile(targetPath)
	if err != nil {
		return fmt.Errorf("read target: %w", err)
	}

	// Read Signature
	sigBytes, err := os.ReadFile(sigPath)
	if err != nil {
		return fmt.Errorf("read sig: %w", err)
	}
	
	// OpenPGP returns entity and error
	// CheckArmoredDetachedSignature takes (keyRing, data, armor)
	_, err = openpgp.CheckArmoredDetachedSignature(keyRing, bytes.NewReader(targetBytes), bytes.NewReader(sigBytes))
	if err != nil {
		return err
	}
	
	fmt.Println("Signature Verified")
	return nil
}
