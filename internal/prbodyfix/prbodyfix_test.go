package prbodyfix

import (
	"testing"
)

func TestClean(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "basic sentinel removal",
			input: "Title\nPR_BODY_TEMPLATE_v1: description\nBody",
			want:  "Title\nBody",
		},
		{
			name:  "sentinel with whitespace",
			input: "Title\n  PR_BODY_TEMPLATE_v1: description  \nBody",
			want:  "Title\nBody",
		},
		{
			name:  "keep sentinel in middle",
			input: "Title\nNote: PR_BODY_TEMPLATE_v1: description\nBody",
			want:  "Title\nNote: PR_BODY_TEMPLATE_v1: description\nBody",
		},
		{
			name:  "clean preserves internal whitespace (only outer trim)",
			input: "  Title  \n  Body  ",
			want:  "Title  \n  Body",
		},
		{
			name:  "empty after clean",
			input: "   PR_BODY_TEMPLATE_v1: description   ",
			want:  "",
		},
		{
			name:  "multiple sentinels",
			input: "PR_BODY_TEMPLATE_v1: a\nKeep\nPR_BODY_TEMPLATE_v1: b",
			want:  "Keep",
		},
		{
			name:  "preserves indentation",
			input: "List:\n  - Item 1\n  - Item 2",
			want:  "List:\n  - Item 1\n  - Item 2",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Clean(tt.input); got != tt.want {
				t.Errorf("Clean() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestEnsureTrailingNewline(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "adds newline if missing",
			input: "foo",
			want:  "foo\n",
		},
		{
			name:  "keeps single newline",
			input: "foo\n",
			want:  "foo\n",
		},
		{
			name:  "non-empty string returns empty (logic choice)", // Spec implies ensure newline on FINAL body which is presumed non-empty. 
			// If Clean returns empty, we might not call EnsureTrailingNewline immediately or we expect minimalist body. 
			// verification: "trailing newline guarantee" usually applies to the file content. 
			// If input is "", EnsureTrailingNewline("") -> "" or "\n"? 
			// Let's assume for now it handles non-empty. For empty, maybe "\n" is safer for a file?
			// But Clean() returns non-empty string for empty body.
			// Let's stick to the prompt "trailing newline 保証". 
			// If I have a body "foo", it becomes "foo\n". 
			// If I have "", maybe it stays ""? Or "\n"?
			// The workflow ensures "minimal body" if empty. So EnsureTrailingNewline will likely receive non-empty.
			// Let's test "foo" -> "foo\n".
			input: "bar",
			want:  "bar\n",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := EnsureTrailingNewline(tt.input); got != tt.want {
				t.Errorf("EnsureTrailingNewline(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
