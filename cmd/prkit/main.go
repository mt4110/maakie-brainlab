package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Sentinel line prefix to strip from template
const SENTINEL_PREFIX = "PR_BODY_TEMPLATE_v1:"

func main() {
	var baseBranch string
	flag.StringVar(&baseBranch, "base", "main", "Base branch to compare against")
	flag.Parse()

	args := flag.Args()
	if len(args) == 0 {
		log.Println("command required: create")
		os.Exit(1)
	}

	cmd := args[0]
	switch cmd {
	case "create":
		if err := runCreate(baseBranch); err != nil {
			log.Printf("error: %v\n", err)
			os.Exit(1)
		}
	default:
		log.Printf("unknown command: %s\n", cmd)
		os.Exit(1)
	}
}

func runCreate(base string) error {
	// 0. Safety Snapshots
	// Check if git repo
	if _, err := exec.Command("git", "rev-parse", "--show-toplevel").Output(); err != nil {
		return errors.New("not a git repo")
	}

	// 1. Get current branch
	current, err := gitOutput("rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return fmt.Errorf("failed to get current branch: %w", err)
	}
	if current == "HEAD" || current == "" {
		return errors.New("headless state or empty branch name")
	}
	if current == base {
		return fmt.Errorf("refuse on base branch: %s", base)
	}

	// Check status porcelain
	status, err := gitOutput("status", "--porcelain")
	if err != nil {
		return fmt.Errorf("git status failed: %w", err)
	}
	if strings.TrimSpace(status) != "" {
		return errors.New("working tree dirty")
	}

	// 2. Resolve Upstream
	// Try origin/base, fallback to base
	upstream := "origin/" + base
	if err := exec.Command("git", "rev-parse", "--verify", upstream).Run(); err != nil {
		fmt.Printf("note: %s not found, falling back to %s\n", upstream, base)
		upstream = base
	}

	// 3. Check commit count diff
	countOut, err := gitOutput("rev-list", "--count", upstream+"..HEAD")
	if err != nil {
		return fmt.Errorf("failed to count commits: %w", err)
	} else if countOut == "0" {
		return fmt.Errorf("STOP: 0 commits diff between %s and HEAD", upstream)
	}
	fmt.Printf("Changes detected: %s commits\n", countOut)

	// 4. Check if PR exists
	checkCmd := exec.Command("gh", "pr", "view", "--json", "url")
	if err := checkCmd.Run(); err == nil {
		fmt.Println("PR exists")
		return nil
	}

	// 5. Prepare Title & Body
	// Title = top commit subject
	title, err := gitOutput("log", "-1", "--pretty=%s")
	if err != nil {
		return fmt.Errorf("failed to get title: %w", err)
	}

	// Body = template -> sentinel removal -> evidence injection
	body := prepareBody(base)

	// Write body to temp file
	tmpFile, err := os.CreateTemp("", "pr_body_*.md")
	if err != nil {
		return fmt.Errorf("create temp: %w", err)
	}
	defer os.Remove(tmpFile.Name())
	if _, err := tmpFile.WriteString(body); err != nil {
		return err
	}
	if err := tmpFile.Close(); err != nil {
		return err
	}

	fmt.Printf("Creating PR '%s' into '%s'...\n", title, base)

	// 6. Execute gh pr create
	ghArgs := []string{"pr", "create", "--base", base, "--head", current, "--title", title, "--body-file", tmpFile.Name()}
	
	ghCmd := exec.Command("gh", ghArgs...)
	ghCmd.Stdout = os.Stdout
	ghCmd.Stderr = os.Stderr
	ghCmd.Stdin = os.Stdin
	
	if err := ghCmd.Run(); err != nil {
		return fmt.Errorf("gh pr create failed: %w", err)
	}

	return nil
}

func prepareBody(base string) string {
	// Try read template
	content, err := os.ReadFile(".github/pull_request_template.md")
	template := string(content)
	if err != nil {
		// Fallback
		template = "## Summary\n(auto)\n\n## Evidence\n"
	}

	// Strip sentinel by line prefix
	lines := strings.Split(template, "\n")
	var cleaned []string
	for _, l := range lines {
		if strings.HasPrefix(strings.TrimSpace(l), SENTINEL_PREFIX) {
			continue
		}
		cleaned = append(cleaned, l)
	}
	body := strings.Join(cleaned, "\n")

	// Inject Evidence
	// Find latest bundle
	bundlePath := findLatestBundle()
	
	evidenceSection := "## Evidence"
	if !strings.Contains(body, evidenceSection) {
		body += "\n\n" + evidenceSection + "\n"
	}

	// Prepare injection lines
	headSHA, _ := gitOutput("rev-parse", "HEAD")
	timestamp := time.Now().UTC().Format(time.RFC3339)
	
	injection := []string{
		fmt.Sprintf("- HeadSHA: `%s`", headSHA),
		fmt.Sprintf("- GeneratedAt: `%s`", timestamp),
	}
	
	if bundlePath != "" {
		baseName := filepath.Base(bundlePath)
		injection = append(injection, fmt.Sprintf("- Bundle: `%s`", baseName))
		
		// Calc SHA256 of bundle
		if sum, err := sha256File(bundlePath); err == nil {
			injection = append(injection, fmt.Sprintf("- SHA256: `%s`", sum))
		}
	} else {
		injection = append(injection, "- Bundle: `(not found)`")
	}

	// Inject under ## Evidence
	body = insertAfter(body, "## Evidence", strings.Join(injection, "\n"))
	
	if strings.TrimSpace(body) == "" {
		return fmt.Sprintf("Minimal Body\n\nHeadSHA: %s\nRun: (auto)", headSHA)
	}

	return body
}

func insertAfter(text, marker, insertion string) string {
	parts := strings.SplitN(text, marker, 2)
	if len(parts) < 2 {
		return text + "\n" + insertion
	}
	return parts[0] + marker + "\n" + insertion + "\n" + parts[1]
}

func findLatestBundle() string {
	// Search paths
	patterns := []string{
		".local/**/review_bundle*.tar.gz",
		".local/**/review_pack*.tar.gz",
		"./review_bundle*.tar.gz",
		"./review_pack*.tar.gz",
	}

	var latestPath string
	var latestTime time.Time

	for _, p := range patterns {
		if strings.Contains(p, "**") {
			root := ".local"
			if _, err := os.Stat(root); err == nil {
				filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
					if err != nil { return nil }
					if !info.IsDir() && (strings.Contains(info.Name(), "review_bundle") || strings.Contains(info.Name(), "review_pack")) && strings.HasSuffix(info.Name(), ".tar.gz") {
						if info.ModTime().After(latestTime) {
							latestTime = info.ModTime()
							latestPath = path
						}
					}
					return nil
				})
			}
			continue
		}
		
		matches, _ := filepath.Glob(p)
		for _, m := range matches {
			info, err := os.Stat(m)
			if err == nil {
				if info.ModTime().After(latestTime) {
					latestTime = info.ModTime()
					latestPath = m
				}
			}
		}
	}
	return latestPath
}

func sha256File(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func gitOutput(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	var out bytes.Buffer
	cmd.Stdout = &out
	err := cmd.Run()
	return strings.TrimSpace(out.String()), err
}
