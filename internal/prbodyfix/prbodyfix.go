package prbodyfix

import (
	"strings"
)

// Sentinel is the prefix marker for lines to be removed.
const Sentinel = "PR_BODY_TEMPLATE_v1:"

// Clean removes lines starting with the sentinel (including HTML comments),
// preserving indentation for others, and trims the result.
func Clean(body string) string {
	lines := strings.Split(body, "\n")
	var keep []string
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// 1. Direct match
		if strings.HasPrefix(trimmed, Sentinel) {
			continue
		}

		// 2. HTML comment match: <!-- PR_BODY_TEMPLATE_v1: ... -->
		if strings.HasPrefix(trimmed, "<!--") {
			// Remove "<!--" and trim again
			commentContent := strings.TrimSpace(strings.TrimPrefix(trimmed, "<!--"))
			if strings.HasPrefix(commentContent, Sentinel) {
				continue
			}
		}

		keep = append(keep, line)
	}
	result := strings.Join(keep, "\n")
	return strings.TrimSpace(result)
}

// EnsureTrailingNewline ensures the string ends with at least one newline if it is not empty.
func EnsureTrailingNewline(s string) string {
	if s == "" {
		return ""
	}
	if strings.HasSuffix(s, "\n") {
		return s
	}
	return s + "\n"
}
