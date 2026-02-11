package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type RetentionConfig struct {
	Version           int                      `json:"version"`
	StoreDir          string                   `json:"store_dir"`
	MaxTotalBytes     int64                    `json:"max_total_bytes"`
	DefaultKeepLast   int                      `json:"default_keep_last"`
	DefaultMaxAgeDays int                      `json:"default_max_age_days"`
	Kinds             map[string]KindRetention `json:"kinds"`
}

type KindRetention struct {
	KeepLast   int `json:"keep_last"`
	MaxAgeDays int `json:"max_age_days"`
}

type PackFile struct {
	Path      string
	Kind      string
	Timestamp time.Time
	Size      int64
	Reason    string // Why it is a candidate for deletion
}

func runGc(args []string) error {
	fs := flag.NewFlagSet("gc", flag.ExitOnError)
	storeFlag := fs.String("store", "", "Store directory (overrides config)")
	apply := fs.Bool("apply", false, "Actually delete files (default is dry-run)")
	configPath := fs.String("config", "ops/evidence_retention.json", "Path to retention config")

	if err := fs.Parse(args); err != nil {
		return err
	}

	// 1. Load Config
	cfg, err := loadConfig(*configPath)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	// Store override
	storeDir := cfg.StoreDir
	if *storeFlag != "" {
		storeDir = *storeFlag
	}
	if storeDir == "" {
		storeDir = ".local/evidence_store"
	}

	fmt.Printf("Store: %s\n", storeDir)
	fmt.Printf("Config: %s\n", *configPath)
	if !*apply {
		fmt.Println("Mode: DRY-RUN (no files will be deleted)")
	} else {
		fmt.Println("Mode: APPLY (files WILL be deleted)")
	}

	// 2. Scan Packs
	packsDir := filepath.Join(storeDir, "packs")
	files, err := scanPacks(packsDir)
	if err != nil {
		if os.IsNotExist(err) {
			fmt.Println("No packs found.")
			return nil
		}
		return fmt.Errorf("failed to scan packs: %w", err)
	}

	// 3. Mark Candidates
	candidates, kept := applyRetentionRules(files, cfg)

	// 4. Output / Delete
	if len(candidates) == 0 {
		fmt.Println("No packs to delete.")
		return nil
	}

	fmt.Println("\nDeletion Candidates:")
	for _, c := range candidates {
		fmt.Printf("[%s] %s (%s, %s)\n", c.Reason, filepath.Base(c.Path), c.Kind, c.Timestamp.Format(time.RFC3339))
	}

	if *apply {
		// Log deletions
		logPath := filepath.Join(storeDir, "gc.log")
		lf, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			return fmt.Errorf("failed to open gc.log: %w", err)
		}
		defer lf.Close()

		fmt.Println("\nDeleting...")
		for _, c := range candidates {
			if err := os.Remove(c.Path); err != nil {
				fmt.Printf("FAILED to delete %s: %v\n", c.Path, err)
			} else {
				fmt.Printf("Deleted: %s\n", c.Path)
				// Log format: Timestamp Action Path Reason
				fmt.Fprintf(lf, "%s\tDELETE\t%s\t%s\n", time.Now().UTC().Format(time.RFC3339), c.Path, c.Reason)
			}
		}
	}

	// 5. Summary
	var keptSize int64
	for _, k := range kept {
		keptSize += k.Size
	}
	fmt.Printf("\nSummary:\n  Candidates: %d\n  Kept: %d (Total Size: %d bytes)\n", len(candidates), len(kept), keptSize)

	return nil
}

func loadConfig(path string) (RetentionConfig, error) {
	var cfg RetentionConfig
	f, err := os.Open(path)
	if err != nil {
		return cfg, err
	}
	defer f.Close()
	err = json.NewDecoder(f).Decode(&cfg)
	return cfg, err
}

func scanPacks(root string) ([]PackFile, error) {
	var files []PackFile
	// Structure: packs/<kind>/filename
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}

	for _, kindEntry := range entries {
		if !kindEntry.IsDir() {
			continue
		}
		kind := kindEntry.Name()
		kindDir := filepath.Join(root, kind)
		
		packEntries, err := os.ReadDir(kindDir)
		if err != nil {
			return nil, err
		}

		for _, pe := range packEntries {
			if pe.IsDir() || !strings.HasSuffix(pe.Name(), ".tar.gz") {
				continue
			}
			// Parse timestamp from filename: evidence_<kind>_<UTC>_<sha>.tar.gz
			// evidence_prverify_20260211T100000Z_abcdef.tar.gz
			parts := strings.Split(pe.Name(), "_")
			if len(parts) < 3 {
				continue
			}
			
			// Find the timestamp part. It's usually parts[len-2] if we assume fixed suffix
			// But kind can have underscores? The contract says kind: [a-z][a-z0-9_]*
			// So parsing is tricky.
			// However, format is: evidence_<kind>_<UTC>_<gitsha>.tar.gz
			// We can work backwards.
			// last: <gitsha>.tar.gz
			// 2nd last: <UTC>
			// rest: evidence_<kind>
			
			if len(parts) < 4 { // evidence, kind..., utc, sha.tar.gz
				continue 
			}
			
			tsStr := parts[len(parts)-2]
			ts, err := time.Parse("20060102T150405Z", tsStr)
			if err != nil {
				// Fallback: file modtime? Or just ignore?
				// Ignore for safety in v1
				continue
			}

			info, err := pe.Info()
			if err != nil {
				continue
			}

			files = append(files, PackFile{
				Path:      filepath.Join(kindDir, pe.Name()),
				Kind:      kind,
				Timestamp: ts,
				Size:      info.Size(),
			})
		}
	}
	return files, nil
}

func applyRetentionRules(files []PackFile, cfg RetentionConfig) ([]PackFile, []PackFile) {
	var candidates []PackFile
	var kept []PackFile

	// Group by kind
	byKind := make(map[string][]PackFile)
	for _, f := range files {
		byKind[f.Kind] = append(byKind[f.Kind], f)
	}

	// Per-kind policies (KeepLast / MaxAge)
	for kind, kindFiles := range byKind {
		// Sort by timestamp descending (newest first)
		sort.Slice(kindFiles, func(i, j int) bool {
			return kindFiles[i].Timestamp.After(kindFiles[j].Timestamp)
		})

		policy, ok := cfg.Kinds[kind]
		keepLast := cfg.DefaultKeepLast
		maxAge := cfg.DefaultMaxAgeDays
		
		if ok {
			if policy.KeepLast > 0 { keepLast = policy.KeepLast }
			if policy.MaxAgeDays > 0 { maxAge = policy.MaxAgeDays }
		}

		now := time.Now().UTC()
		
		for i, f := range kindFiles {
			// Rule 1: Keep Last N
			if i < keepLast {
				// Rule 2: Max Age (only if we have kept enough? Or strictly max age?)
				// Usually "Keep Last N" overrides "Max Age" to prevent deleting everything.
				// But user prompt says "kind ごとに keep_last 超過分を “古い順” で候補化, max_age_days 超過分を候補化"
				// Usually this means: "If older than X days AND index >= keepLast"
				// Let's assume keepLast protects files even if old.
				
				// Wait, "defaults: keep_last=30". If I have 1 file 2 years old, do I keep it?
				// Usually yes, to have *some* history.
				
				kept = append(kept, f)
			} else {
				// Candidate for deletion?
				// Check max age.
				ageDays := int(now.Sub(f.Timestamp).Hours() / 24)
				if ageDays > maxAge {
					f.Reason = fmt.Sprintf("MaxAge(%d days) > %d", ageDays, maxAge)
					candidates = append(candidates, f)
				} else {
					f.Reason = fmt.Sprintf("Excess KeepLast(%d)", keepLast)
					candidates = append(candidates, f)
				}
			}
		}
	}

	// Rule 3: Max Total Bytes (Global)
	// We check the 'kept' files. If total size > limit, we drop oldest.
	var totalSize int64
	for _, f := range kept {
		totalSize += f.Size
	}

	if totalSize > cfg.MaxTotalBytes {
		// Sort kept by timestamp ascending (oldest first) to pick victims
		sort.Slice(kept, func(i, j int) bool {
			return kept[i].Timestamp.Before(kept[j].Timestamp)
		})

		var newKept []PackFile
		// We remove from 'kept' and move to 'candidates'
		// Iterate and drop until size matches
		
		// Actually, simpler to rebuild 'newKept' from end (newest)
		// But we need to drop oldest.
		
		for _, f := range kept {
			if totalSize > cfg.MaxTotalBytes {
				f.Reason = fmt.Sprintf("MaxTotalBytes(%d) exceeded", cfg.MaxTotalBytes)
				candidates = append(candidates, f)
				totalSize -= f.Size
			} else {
				newKept = append(newKept, f)
			}
		}
		kept = newKept
	}

	return candidates, kept
}
