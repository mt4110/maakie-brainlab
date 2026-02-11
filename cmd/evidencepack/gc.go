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

	storeDir := resolveStoreDir(cfg.StoreDir, *storeFlag)

	fmt.Printf("Store: %s\n", storeDir)
	fmt.Printf("Config: %s\n", *configPath)
	printGCMode(*apply)

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

	printCandidates(candidates)

	if *apply {
		if err := executeDeletions(candidates, storeDir); err != nil {
			return err
		}
	}

	// 5. Summary
	printGCSummary(candidates, kept)
	return nil
}

func resolveStoreDir(cfgDir, flagDir string) string {
	if flagDir != "" {
		return flagDir
	}
	if cfgDir != "" {
		return cfgDir
	}
	return ".local/evidence_store"
}

func printGCMode(apply bool) {
	if apply {
		fmt.Println("Mode: APPLY (files WILL be deleted)")
	} else {
		fmt.Println("Mode: DRY-RUN (no files will be deleted)")
	}
}

func printCandidates(candidates []PackFile) {
	fmt.Println("\nDeletion Candidates:")
	for _, c := range candidates {
		fmt.Printf("[%s] %s (%s, %s)\n", c.Reason, filepath.Base(c.Path), c.Kind, c.Timestamp.Format(time.RFC3339))
	}
}

func executeDeletions(candidates []PackFile, storeDir string) error {
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
			fmt.Fprintf(lf, "%s\tDELETE\t%s\t%s\n", time.Now().UTC().Format(time.RFC3339), c.Path, c.Reason)
		}
	}
	return nil
}

func printGCSummary(candidates, kept []PackFile) {
	var keptSize int64
	for _, k := range kept {
		keptSize += k.Size
	}
	fmt.Printf("\nSummary:\n  Candidates: %d\n  Kept: %d (Total Size: %d bytes)\n", len(candidates), len(kept), keptSize)
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
			pf, ok := parsePackFile(pe, kind, kindDir)
			if ok {
				files = append(files, pf)
			}
		}
	}
	return files, nil
}

func parsePackFile(pe os.DirEntry, kind, kindDir string) (PackFile, bool) {
	if pe.IsDir() || !strings.HasSuffix(pe.Name(), ".tar.gz") {
		return PackFile{}, false
	}

	parts := strings.Split(pe.Name(), "_")
	if len(parts) < 4 {
		return PackFile{}, false
	}

	tsStr := parts[len(parts)-2]
	ts, err := time.Parse("20060102T150405Z", tsStr)
	if err != nil {
		return PackFile{}, false
	}

	info, err := pe.Info()
	if err != nil {
		return PackFile{}, false
	}

	return PackFile{
		Path:      filepath.Join(kindDir, pe.Name()),
		Kind:      kind,
		Timestamp: ts,
		Size:      info.Size(),
	}, true
}

func applyRetentionRules(files []PackFile, cfg RetentionConfig) ([]PackFile, []PackFile) {
	var candidates []PackFile
	var kept []PackFile

	// Group by kind
	byKind := make(map[string][]PackFile)
	for _, f := range files {
		byKind[f.Kind] = append(byKind[f.Kind], f)
	}

	// Per-kind policies
	for kind, kindFiles := range byKind {
		sort.Slice(kindFiles, func(i, j int) bool {
			return kindFiles[i].Timestamp.After(kindFiles[j].Timestamp)
		})
		c, k := applyKindRetention(kindFiles, kind, cfg)
		candidates = append(candidates, c...)
		kept = append(kept, k...)
	}

	// Rule 3: Max Total Bytes (Global)
	candidates, kept = enforceTotalBytesLimit(candidates, kept, cfg.MaxTotalBytes)
	return candidates, kept
}

func applyKindRetention(kindFiles []PackFile, kind string, cfg RetentionConfig) ([]PackFile, []PackFile) {
	var candidates, kept []PackFile

	policy, ok := cfg.Kinds[kind]
	keepLast := cfg.DefaultKeepLast
	maxAge := cfg.DefaultMaxAgeDays
	if ok {
		if policy.KeepLast > 0 {
			keepLast = policy.KeepLast
		}
		if policy.MaxAgeDays > 0 {
			maxAge = policy.MaxAgeDays
		}
	}

	now := time.Now().UTC()
	for i, f := range kindFiles {
		if i < keepLast {
			kept = append(kept, f)
		} else {
			ageDays := int(now.Sub(f.Timestamp).Hours() / 24)
			if ageDays > maxAge {
				f.Reason = fmt.Sprintf("MaxAge(%d days) > %d", ageDays, maxAge)
			} else {
				f.Reason = fmt.Sprintf("Excess KeepLast(%d)", keepLast)
			}
			candidates = append(candidates, f)
		}
	}
	return candidates, kept
}

func enforceTotalBytesLimit(candidates, kept []PackFile, maxTotalBytes int64) ([]PackFile, []PackFile) {
	var totalSize int64
	for _, f := range kept {
		totalSize += f.Size
	}
	if totalSize <= maxTotalBytes {
		return candidates, kept
	}

	sort.Slice(kept, func(i, j int) bool {
		return kept[i].Timestamp.Before(kept[j].Timestamp)
	})

	var newKept []PackFile
	for _, f := range kept {
		if totalSize > maxTotalBytes {
			f.Reason = fmt.Sprintf("MaxTotalBytes(%d) exceeded", maxTotalBytes)
			candidates = append(candidates, f)
			totalSize -= f.Size
		} else {
			newKept = append(newKept, f)
		}
	}
	return candidates, newKept
}
