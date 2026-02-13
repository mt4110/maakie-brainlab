package reviewpack

// Run is the main entry point for the reviewpack tool.
func Run(args []string) int {
	if len(args) < 2 {
		usage()
		return 1
	}

	subCmd := args[1]
	cmdArgs := args[2:]

	switch subCmd {
	case "pack":
		runPack(cmdArgs)
	case "verify":
		runVerify(cmdArgs)
	case "submit":
		runSubmit(cmdArgs)
	case "repro-check":
		runReproCheck(cmdArgs)
	case "diff":
		return runDiff(cmdArgs)
	default:
		usage()
		return 1
	}
	return 0
}
