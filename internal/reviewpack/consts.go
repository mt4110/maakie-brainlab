package reviewpack

const (
	defaultTimeboxSec = 300
	packPrefix        = "review_bundle"

	// Constants for logging and filenames
	msgFatalMkdirTemp  = "[FATAL] MkdirTemp: %v"
	msgFatalMkdirAll   = "[FATAL] MkdirAll: %v"
	msgDebugPreflight  = "DEBUG: Starting preflight checks..."
	msgFatalGitStatus  = "[FATAL] git status --porcelain failed: %v"
	msgFatalSha256     = "[FATAL] sha256 %s: %v"
	msgFatalStat       = "[FATAL] stat %s: %v"
	fileStatus         = "01_status.txt"
	fileGitLog         = "10_git_log.txt"
	fileGitDiff        = "11_git_diff.patch"
	fileMakeTest       = "30_make_test.log"
	fileMakeEval       = "31_make_run_eval.log"
	fileSelfVerify     = "40_self_verify.log"
	fileManifest       = "MANIFEST.tsv"
	fileChecksums      = "CHECKSUMS.sha256"
	filePackVersion    = "PACK_VERSION"
	fileSpec           = "SPEC.md"
	fileLatestJsonl    = "eval/results/latest.jsonl"
	extTarGz           = ".tar.gz"
	dirSrcSnapshot     = "src_snapshot"
	dirEvalResults     = "eval/results"

	// Refactoring Constants
	msgFatalCreate = "[FATAL] create %s: %v"
	msgFatalMkdir  = "[FATAL] mkdir %s: %v"
	msgFatalWrite  = "[FATAL] write %s: %v"
	codeBlockBash  = "```bash"
)
