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

	if err := dispatch(cmd, args); err != nil {
		fmt.Fprintf(os.Stderr, errorFormat, err)
		exitCode := 1
		if he, ok := err.(*HealthError); ok {
			exitCode = he.Code
		}
		if ve, ok := err.(*VerifyError); ok {
			exitCode = ve.Code
		}
		os.Exit(exitCode)
	}
}

// commands maps subcommand names to their handler functions.
var commands = map[string]func([]string) error{
	CmdPack:   runPack,
	CmdVerify: runVerify,
	CmdLs:     runLs,
	CmdGc:     runGc,
	CmdBundle: runBundle,
	CmdHealth: runHealth,
	CmdKinds:  runKinds,
}

func dispatch(cmd string, args []string) error {
	handler, ok := commands[cmd]
	if !ok {
		usage()
		return fmt.Errorf("unknown command: %s", cmd)
	}
	return handler(args)
}

func usage() {
	fmt.Fprintf(os.Stderr, "Usage: evidencepack <subcommand> [args]\n")
	fmt.Fprintf(os.Stderr, "Subcommands:\n")
	fmt.Fprintf(os.Stderr, "  pack    Create a new evidence pack\n")
	fmt.Fprintf(os.Stderr, "  verify  Verify an evidence pack contract\n")
	fmt.Fprintf(os.Stderr, "  ls      List evidence packs in store\n")
	fmt.Fprintf(os.Stderr, "  gc      Garbage collect old evidence packs\n")
	fmt.Fprintf(os.Stderr, "  health  Diagnose audit chain and local state\n")
	fmt.Fprintf(os.Stderr, "  kinds   List known evidence kinds in store\n")
}

// Stubs removed. Implementations are in separate files.
