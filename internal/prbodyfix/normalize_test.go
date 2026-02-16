package prbodyfix

import (
	"strings"
	"testing"
)

func TestNormalize(t *testing.T) {
	tests := []struct {
		name         string
		current      string
		template     string
		headSHA      string
		runURL       string
		wantContains []string
		wantSuffix   string
	}{
		{
			name:     "clean body shouldn't change much",
			current:  "Summary\nMy changes",
			template: "PR_BODY_TEMPLATE_v1: remove me",
			headSHA:  "sha123",
			runURL:   "http://run",
			wantContains: []string{
				"Summary", "My changes",
				"## Evidence",
				"- HeadSHA: `sha123`",
				"- Run: http://run",
			},
			wantSuffix: "\n",
		},
		{
			name:     "sentinel removal impact",
			current:  "PR_BODY_TEMPLATE_v1: remove me\nReal Content",
			template: "PR_BODY_TEMPLATE_v1: remove me",
			headSHA:  "sha123",
			runURL:   "http://run",
			wantContains: []string{
				"Real Content",
			},
		},
		{
			name:     "empty body falls back to template",
			current:  "",
			template: "PR_BODY_TEMPLATE_v1: remove me\nTemplate Content",
			headSHA:  "sha123",
			runURL:   "http://run",
			wantContains: []string{
				"Template Content",
			},
		},
		{
			name:     "empty body and empty template falls back to minimal",
			current:  "",
			template: "", // or pure sentinel
			headSHA:  "sha123",
			runURL:   "http://run",
			wantContains: []string{
				"Minimal Body",
				"HeadSHA: sha123",
				"Run: http://run",
			},
		},
		{
			name:     "idempotency",
			current:  "Content\n\n## Evidence\n- HeadSHA: `sha123`\n- Run: http://run\n",
			template: "",
			headSHA:  "sha123",
			runURL:   "http://run",
			wantContains: []string{
				"Content",
				"## Evidence",
				"- HeadSHA: `sha123`",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Normalize(tt.current, tt.template, tt.headSHA, tt.runURL)

			for _, want := range tt.wantContains {
				if !strings.Contains(got, want) {
					t.Errorf("Normalize() missing %q\ngot:\n%s", want, got)
				}
			}

			if strings.Contains(got, SentinelPrefix) {
				t.Errorf("Normalize() still contains sentinel")
			}

			if !strings.HasSuffix(got, "\n") {
				t.Errorf("Normalize() missing trailing newline")
			}

			// Idempotency Check
			got2 := Normalize(got, tt.template, tt.headSHA, tt.runURL)
			if got != got2 {
				t.Errorf("Normalize() not idempotent.\nFirst:\n%q\nSecond:\n%q", got, got2)
			}
		})
	}
}
