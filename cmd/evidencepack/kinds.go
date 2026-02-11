package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

const CmdKinds = "kinds"

func runKinds(args []string) error {
	fs := flag.NewFlagSet("kinds", flag.ExitOnError)
	store := fs.String("store", ".local/evidence_store", "Store directory")
	if err := fs.Parse(args); err != nil {
		return err
	}

	kinds, err := listKinds(*store)
	if err != nil {
		return fmt.Errorf("failed to list kinds: %w", err)
	}

	if len(kinds) == 0 {
		fmt.Println("No kinds found in store.")
		fmt.Printf("Hint: Create a pack with 'evidencepack pack --kind <name> --store %s ...'\n", *store)
		return nil
	}

	for _, k := range kinds {
		fmt.Println(k)
	}
	return nil
}

func listKinds(storeDir string) ([]string, error) {
	packsDir := filepath.Join(storeDir, "packs")
	entries, err := os.ReadDir(packsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return []string{}, nil
		}
		return nil, err
	}

	var kinds []string
	for _, entry := range entries {
		if entry.IsDir() {
			kinds = append(kinds, entry.Name())
		}
	}
	sort.Strings(kinds)
	return kinds, nil
}
