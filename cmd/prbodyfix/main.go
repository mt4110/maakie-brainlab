package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"reviewpack/internal/prbodyfix"
)

type Event struct {
	PullRequest *PullRequest `json:"pull_request"`
}

type PullRequest struct {
	Number int    `json:"number"`
	Body   string `json:"body"`
	Head   Head   `json:"head"`
	Base   Base   `json:"base"`
}

type Head struct {
	SHA  string `json:"sha"`
	Repo Repo   `json:"repo"`
}

type Base struct {
	SHA  string `json:"sha"`
	Repo Repo   `json:"repo"`
}

type Repo struct {
	FullName string `json:"full_name"`
	Owner    User   `json:"owner"`
	Name     string `json:"name"`
}

type User struct {
	Login string `json:"login"`
}

func main() {
	log.SetFlags(0)

	// 1. Read Event
	eventPath := os.Getenv("GITHUB_EVENT_PATH")
	if eventPath == "" {
		log.Fatal("GITHUB_EVENT_PATH not set")
	}
	eventData, err := os.ReadFile(eventPath)
	if err != nil {
		log.Fatalf("Failed to read event path: %v", err)
	}

	var event Event
	if err := json.Unmarshal(eventData, &event); err != nil {
		log.Fatalf("Failed to parse event JSON: %v", err)
	}
	pr := event.PullRequest
	if pr == nil {
		log.Println("Not a pull_request event. Exiting.")
		return
	}

	// 2. Fork Check
	repoEnv := os.Getenv("GITHUB_REPOSITORY") // owner/repo
	if repoEnv == "" {
		// fallback to event data if env missing (local run?)
		repoEnv = pr.Base.Repo.FullName
	}
	
	if pr.Head.Repo.FullName != repoEnv {
		log.Printf("Fork PR detected (%s != %s). Skipping body check.", pr.Head.Repo.FullName, repoEnv)
		return
	}

	// 3. Logic
	currentBody := pr.Body
	cleaned := prbodyfix.Clean(currentBody)
	needsUpdate := (currentBody != cleaned)
	if needsUpdate {
		log.Println("Sentinel detected or body unclean. Cleaning...")
		currentBody = cleaned
	}

	// 4. Empty Check
	if len(currentBody) == 0 {
		log.Println("Body is empty. Fetching template...")
		tpl, err := fetchTemplate(pr.Base.Repo.Owner.Login, pr.Base.Repo.Name, pr.Base.SHA)
		if err != nil {
			log.Printf("Failed to fetch template: %v", err)
			tpl = ""
		}
		
		filled := prbodyfix.Clean(tpl)
		if len(filled) > 0 {
			currentBody = filled
			needsUpdate = true
			log.Println("Used template.")
		} else {
			log.Println("Template unavailable or empty. Using minimal body.")
			serverUrl := os.Getenv("GITHUB_SERVER_URL")
			if serverUrl == "" {
				serverUrl = "https://github.com"
			}
			runId := os.Getenv("GITHUB_RUN_ID")
			currentBody = fmt.Sprintf("Minimal Body\n\nHeadSHA: %s\nRun: %s/%s/actions/runs/%s",
				pr.Head.SHA, serverUrl, repoEnv, runId)
			needsUpdate = true
		}
	}

	// 5. Trailing Newline
	finalBody := prbodyfix.EnsureTrailingNewline(currentBody)
	if finalBody != pr.Body {
		needsUpdate = true
	}

	// 6. Update if needed
	if needsUpdate {
		if err := updatePR(pr.Base.Repo.Owner.Login, pr.Base.Repo.Name, pr.Number, finalBody); err != nil {
			log.Fatalf("Failed to update PR: %v", err)
		}
		log.Println("PR body updated successfully.")
	} else {
		log.Println("PR body satisfies requirements.")
	}
}

func fetchTemplate(owner, repo, sha string) (string, error) {
	token := os.Getenv("GITHUB_TOKEN")
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/contents/.github/pull_request_template.md?ref=%s", owner, repo, sha)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 404 {
		return "", nil // Not found is fine, return empty
	}
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("api status %s", resp.Status)
	}

	var parsed struct {
		Content  string `json:"content"`
		Encoding string `json:"encoding"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		return "", err
	}

	if parsed.Encoding == "base64" {
		// GitHub API returns base64 with newlines, we need to handle that?
		// StdEncoding handles it? No, typically parsed.Content might have \n. 
		// But let's assume standard behavior or use specific decoder.
		// Actually `encoding/base64` keys on standard padding.
		// `parsed.Content` often comes as a single string? Or with newlines?
		// GitHub API docs say: "The content is encoded ... and may contain line breaks."
		// `base64.StdEncoding.DecodeString` fails on newlines.
		// We should strip newlines.
		cleanContent := strings.ReplaceAll(parsed.Content, "\n", "")
		decoded, err := base64.StdEncoding.DecodeString(cleanContent)
		if err != nil {
			return "", err
		}
		return string(decoded), nil
	}
	return parsed.Content, nil // assume raw or utf8 if not base64?
}

func updatePR(owner, repo string, number int, body string) error {
	token := os.Getenv("GITHUB_TOKEN")
	if token == "" {
		log.Println("GITHUB_TOKEN not set. Skipping update (dry-run).")
		return nil
	}

	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/pulls/%d", owner, repo, number)
	payload := map[string]string{"body": body}
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("PATCH", url, bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("api status %s: %s", resp.Status, string(bodyBytes))
	}
	return nil
}
