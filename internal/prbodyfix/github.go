package prbodyfix

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type GitHubClient struct {
	Token string
}

func NewGitHubClient(token string) *GitHubClient {
	return &GitHubClient{Token: token}
}

func (c *GitHubClient) FetchPRBody(owner, repo string, number int) (string, error) {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/pulls/%d", owner, repo, number)
	resp, err := c.doRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("failed to fetch PR: status %d", resp.StatusCode)
	}

	var payload struct {
		Body string `json:"body"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return "", err
	}
	return payload.Body, nil
}

func (c *GitHubClient) FetchTemplate(owner, repo, ref string) (string, error) {
	// ref is optional, but robust to specify baseSHA
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/contents/.github/pull_request_template.md", owner, repo)
	if ref != "" {
		url += fmt.Sprintf("?ref=%s", ref)
	}

	resp, err := c.doRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return "", nil // Not found is valid (empty)
	}
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("failed to fetch template: status %d", resp.StatusCode)
	}

	var payload struct {
		Content  string `json:"content"`
		Encoding string `json:"encoding"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return "", err
	}

	if payload.Encoding == "base64" {
		decoded, err := base64.StdEncoding.DecodeString(payload.Content)
		if err != nil {
			return "", fmt.Errorf("failed to decode base64: %w", err)
		}
		return string(decoded), nil
	}
	// assume utf8 or raw if not base64? api usually returns base64
	return payload.Content, nil
}

func (c *GitHubClient) UpdatePRBody(owner, repo string, number int, body string) error {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/pulls/%d", owner, repo, number)

	payload := map[string]string{
		"body": body,
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	resp, err := c.doRequest("PATCH", url, bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to update PR: status %d, body: %s", resp.StatusCode, string(bodyBytes))
	}
	return nil
}

func (c *GitHubClient) doRequest(method, url string, body io.Reader) (*http.Response, error) {
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "token "+c.Token)
	req.Header.Set("Accept", "application/vnd.github.v3+json")

	client := &http.Client{Timeout: 10 * time.Second}
	return client.Do(req)
}
