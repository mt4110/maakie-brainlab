package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/tabwriter"
)

func runLs(args []string) error {
	fs := flag.NewFlagSet("ls", flag.ExitOnError)
	store := fs.String("store", ".local/evidence_store", "Store directory")
	kind := fs.String("kind", "", "Filter by kind")
	if err := fs.Parse(args); err != nil {
		return err
	}

	indexPath := filepath.Join(*store, "index", "packs.tsv")
	f, err := os.Open(indexPath)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Println("No evidence packs found (index missing)")
			return nil
		}
		return fmt.Errorf("failed to open index: %w", err)
	}
	defer f.Close()

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "CREATED_AT\tKIND\tFILENAME\tGIT_SHA\tSHA256\tSIZE")

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		parts := strings.Split(line, "\t")
		// Expected: created_at_utc, kind, filename, git_sha, sha256, size
		if len(parts) < 6 {
			continue // Skip malformed lines
		}

		entryKind := parts[1]
		if *kind != "" && entryKind != *kind {
			continue
		}

		fmt.Fprintln(w, line)
	}
	w.Flush()

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading index: %w", err)
	}
	return nil
}
