package main

import (
	"fmt"
	"os"
	"regexp"
)

// Subcommands
const (
	CmdPack   = "pack"
	CmdVerify = "verify"
	CmdLs     = "ls"
	CmdGc     = "gc"
	CmdBundle = "bundle"

	errorFormat = "Error: %v\n"
)

var kindRegex = regexp.MustCompile(`^[a-z][a-z0-9_]{0,31}$`)

func validateKind(k string) error {
	if !kindRegex.MatchString(k) {
		return fmt.Errorf("invalid kind %q: must match %s", k, kindRegex.String())
	}
	return nil
}

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	switch cmd {
	case CmdPack:
		if err := runPack(args); err != nil {
			fmt.Fprintf(os.Stderr, errorFormat, err)
			os.Exit(1)
		}
	case CmdVerify:
		if err := runVerify(args); err != nil {
			fmt.Fprintf(os.Stderr, errorFormat, err)
			os.Exit(1)
		}
	case CmdLs:
		if err := runLs(args); err != nil {
			fmt.Fprintf(os.Stderr, errorFormat, err)
			os.Exit(1)
		}
	case CmdGc:
		if err := runGc(args); err != nil {
			fmt.Fprintf(os.Stderr, errorFormat, err)
			os.Exit(1)
		}
	case CmdBundle:
		if err := runBundle(args); err != nil {
			fmt.Fprintf(os.Stderr, errorFormat, err)
			os.Exit(1)
		}
	default:
		usage()
		os.Exit(1)
	}
}

func usage() {
	fmt.Fprintf(os.Stderr, "Usage: evidencepack <subcommand> [args]\n")
	fmt.Fprintf(os.Stderr, "Subcommands:\n")
	fmt.Fprintf(os.Stderr, "  pack    Create a new evidence pack\n")
	fmt.Fprintf(os.Stderr, "  verify  Verify an evidence pack contract\n")
	fmt.Fprintf(os.Stderr, "  ls      List evidence packs in store\n")
	fmt.Fprintf(os.Stderr, "  gc      Garbage collect old evidence packs\n")
}

// Stubs removed. Implementations are in separate files.
