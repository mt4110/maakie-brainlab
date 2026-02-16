package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"

	"reviewpack/internal/prbodyfix"
)

type StartParams struct {
	Owner   string
	Repo    string
	Number  int
	HeadSHA string
	BaseSHA string
	RunURL  string
	IsFork  bool
}

func main() {
	log.SetFlags(0)
	log.SetPrefix("prbodyfix: ")

	// Mode detection
	eventPath := os.Getenv("GITHUB_EVENT_PATH")

	var params StartParams
	var err error

	if eventPath != "" {
		params, err = parseEventParams(eventPath)
	} else {
		params, err = parseLocalParams()
	}

	if err != nil {
		log.Fatalf("error: %v", err)
	}

	if params.IsFork {
		log.Println("SKIP: fork PR detected (no write permission)")
		return
	}

	// Token
	token := os.Getenv("GITHUB_TOKEN")
	if token == "" {
		token = os.Getenv("GH_TOKEN")
	}
	if token == "" {
		out, err := exec.Command("gh", "auth", "token").Output()
		if err == nil {
			token = strings.TrimSpace(string(out))
		}
	}
	if token == "" {
		log.Fatal("error: missing GITHUB_TOKEN/GH_TOKEN")
	}

	client := prbodyfix.NewGitHubClient(token)

	// Fetch Current
	log.Printf("Fetching PR #%d from %s/%s...\n", params.Number, params.Owner, params.Repo)
	currentBody, err := client.FetchPRBody(params.Owner, params.Repo, params.Number)
	if err != nil {
		log.Fatalf("error: fetch pr failed: %v", err)
	}

	// Fetch Template
	template, err := client.FetchTemplate(params.Owner, params.Repo, params.BaseSHA)
	if err != nil {
		log.Printf("warning: fetch template failed (using empty): %v", err)
		template = ""
	}

	// Normalize
	log.Println("Normalizing body...")
	runURL := params.RunURL
	if runURL == "" {
		runURL = "(local run)"
	}
	desired := prbodyfix.Normalize(currentBody, template, params.HeadSHA, runURL)

	// Update if needed
	if desired == currentBody {
		log.Println("PASS: Body is compliant (idempotent)")
		return
	}

	log.Println("Updating PR body...")
	if err := client.UpdatePRBody(params.Owner, params.Repo, params.Number, desired); err != nil {
		log.Fatalf("error: update pr failed: %v", err)
	}
	log.Println("PASS: Body updated")
}

func parseEventParams(path string) (StartParams, error) {
	f, err := os.Open(path)
	if err != nil {
		return StartParams{}, err
	}
	defer f.Close()

	var event struct {
		PullRequest struct {
			Number int `json:"number"`
			Head   struct {
				SHA  string `json:"sha"`
				Repo struct {
					FullName string `json:"full_name"`
				} `json:"repo"`
			} `json:"head"`
			Base struct {
				SHA string `json:"sha"`
			} `json:"base"`
		} `json:"pull_request"`
		Repository struct {
			Owner struct {
				Login string `json:"login"`
			} `json:"owner"`
			Name string `json:"name"`
		} `json:"repository"`
	}

	if err := json.NewDecoder(f).Decode(&event); err != nil {
		return StartParams{}, err
	}

	p := StartParams{
		Owner:   event.Repository.Owner.Login,
		Repo:    event.Repository.Name,
		Number:  event.PullRequest.Number,
		HeadSHA: event.PullRequest.Head.SHA,
		BaseSHA: event.PullRequest.Base.SHA,
	}

	// Validation
	if p.Number == 0 || p.Owner == "" || p.Repo == "" {
		return p, fmt.Errorf("invalid event json (missing number/owner/repo)")
	}

	// Fork check
	targetRepo := fmt.Sprintf("%s/%s", p.Owner, p.Repo)
	if event.PullRequest.Head.Repo.FullName != targetRepo && event.PullRequest.Head.Repo.FullName != "" {
		p.IsFork = true
	}

	// Run URL construction
	server := os.Getenv("GITHUB_SERVER_URL")
	if server == "" {
		server = "https://github.com"
	}
	p.RunURL = fmt.Sprintf("%s/%s/%s/actions/runs/%s", server, p.Owner, p.Repo, os.Getenv("GITHUB_RUN_ID"))

	return p, nil
}

func parseLocalParams() (StartParams, error) {
	var prNum int
	var repo string
	flag.IntVar(&prNum, "pr", 0, "PR number")
	flag.StringVar(&repo, "repo", "", "Owner/Repo")
	flag.Parse()

	if prNum == 0 {
		return StartParams{}, fmt.Errorf("local mode requires --pr <number>")
	}

	if repo == "" {
		// try git remote
		out, err := exec.Command("git", "remote", "get-url", "origin").Output()
		if err == nil {
			s := strings.TrimSpace(string(out))
			// git@github.com:owner/repo.git or https://github.com/owner/repo.git
			s = strings.TrimSuffix(s, ".git")
			if idx := strings.LastIndex(s, ":"); idx != -1 {
				repo = s[idx+1:]
			} else if idx := strings.LastIndex(s, "/"); idx != -1 {
				// fallback for https, strict parsing difficult without heavy logic
				// but simplistic approach:
				parts := strings.Split(s, "/")
				if len(parts) >= 2 {
					repo = parts[len(parts)-2] + "/" + parts[len(parts)-1]
				}
			}
		}
	}
	if repo == "" {
		return StartParams{}, fmt.Errorf("repo not detected, use --repo owner/name")
	}

	parts := strings.Split(repo, "/")
	if len(parts) != 2 {
		return StartParams{}, fmt.Errorf("invalid repo format %s", repo)
	}

	// SHA logic for local is best effort or explicit args (not implemented yet for simplicity)
	// We can use current HEAD for headSHA
	headSHA := "HEAD"
	// BaseSHA? we might not know.

	return StartParams{
		Owner:   parts[0],
		Repo:    parts[1],
		Number:  prNum,
		HeadSHA: headSHA,
		BaseSHA: "main", // Assumption for local test
		RunURL:  "(local run)",
		IsFork:  false, // Assume local user has permissions
	}, nil
}
