package main

import "crypto/sha256"

// sha256Bytes returns a copy of sha256 digest bytes (stable slice).
func sha256Bytes(b []byte) []byte {
	sum := sha256.Sum256(b)
	out := make([]byte, sha256.Size)
	copy(out, sum[:])
	return out
}
