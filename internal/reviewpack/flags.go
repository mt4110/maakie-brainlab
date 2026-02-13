package reviewpack

import (
	"fmt"
	"os"
)

func usage() {
	fmt.Fprintf(os.Stderr, "Usage: reviewpack <command> [args]\n")
	fmt.Fprintf(os.Stderr, "Commands:\n")
	fmt.Fprintf(os.Stderr, "  pack [--timebox N] [--skip-eval] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  verify <dir|tar.gz>\n")
	fmt.Fprintf(os.Stderr, "  submit [--timebox N] [--mode strict|verify-only] [--skip-test] [N_COMMITS]\n")
	fmt.Fprintf(os.Stderr, "  repro-check\n")
	fmt.Fprintf(os.Stderr, "  diff <bundleA> <bundleB>\n")
}
