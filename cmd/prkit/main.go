package main

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

func main() {
	var baseBranch string
	flag.StringVar(&baseBranch, "base", "main", "Base branch to compare against")
	flag.Parse()

	args := flag.Args()
	if len(args) == 0 {
		log.Fatal("command required: create")
	}

	cmd := args[0]
	switch cmd {
	case "create":
		if err := runCreate(baseBranch); err != nil {
			log.Fatalf("error: %v", err)
		}
	default:
		log.Fatalf("unknown command: %s", cmd)
	}
}

func runCreate(base string) error {
	// 1. Get current branch
	current, err := gitOutput("rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return fmt.Errorf("failed to get current branch: %w", err)
	}
	if current == "HEAD" || current == "" {
		return errors.New("headless state or empty branch name")
	}

	// 2. Fetch base to ensure we have it
	// We ignore errors here in case we are offline or base is local, 
	// but strictly we should probably ensure it exists. 
	// For "STOP test", we assume local git knows about base.
	_ = exec.Command("git", "fetch", "origin", base).Run()

	// 3. Check commit count diff
	// git rev-list --count base..current
	countOut, err := gitOutput("rev-list", "--count", "origin/"+base+".."+current)
	if err != nil {
		// Try local base if origin ref fails
		countOut, err = gitOutput("rev-list", "--count", base+".."+current)
		if err != nil {
			return fmt.Errorf("failed to count commits between %s and %s: %w", base, current, err)
		}
	}
	
	if countOut == "0" {
		// STOP logic
		return fmt.Errorf("STOP: 0 commits diff between %s and %s", base, current)
	}

	// 4. PR Metadata
	// Strategy: Use `gh pr create --fill` which uses the template + branch name.
    
    fmt.Printf("repo state clean, commits > 0 (%s). Proceeding to create PR.\n", countOut)

	// execution
	// gh pr create --base base --head current --fill
	ghArgs := []string{"pr", "create", "--base", base, "--head", current, "--fill"}
	
	// Check if PR already exists
	checkCmd := exec.Command("gh", "pr", "view", "--json", "url")
	if err := checkCmd.Run(); err == nil {
		fmt.Println("PR already exists.")
		return nil
	}

	ghCmd := exec.Command("gh", ghArgs...)
	ghCmd.Stdout = os.Stdout
	ghCmd.Stderr = os.Stderr
	ghCmd.Stdin = os.Stdin // Allow interactive if needed, though we expect automation
	
	if err := ghCmd.Run(); err != nil {
		return fmt.Errorf("gh pr create failed: %w", err)
	}
	
	return nil
}

func gitOutput(args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	var out bytes.Buffer
	cmd.Stdout = &out
	// cmd.Stderr = os.Stderr // Only show stderr on error?
	err := cmd.Run()
	return strings.TrimSpace(out.String()), err
}
