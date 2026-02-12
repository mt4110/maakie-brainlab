package reviewpack

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

func runCmd(dir, name string, args ...string) {
	// Simple wrapper for executing commands and handling redirection syntax roughly
	var cmdArgs []string
	var outFile string

	for i, arg := range args {
		if arg == ">" {
			if i+1 < len(args) {
				outFile = args[i+1]
				cmdArgs = args[:i]
				break
			}
		}
	}
	if outFile == "" {
		cmdArgs = args
	}

	c := exec.Command(name, cmdArgs...)
	c.Dir = dir

	if outFile != "" {
		f, err := os.Create(outFile)
		if err != nil {
			log.Fatalf(msgFatalCreate, outFile, err)
		}
		defer f.Close()
		c.Stdout = f
		c.Stderr = os.Stderr // usually stderr goes to screen
	}

	if err := c.Run(); err != nil {
		log.Fatalf("[FATAL] %s %v failed: %v", name, cmdArgs, err)
	}
}

func runMake(dir, logName string, cmdArgs []string, timeoutSec int, failCode int) {
	logPath := filepath.Join(dir, logName)
	logFile, err := os.Create(logPath)
	if err != nil {
		log.Fatal(err)
	}
	defer logFile.Close()

	ctxCmd := exec.Command(cmdArgs[0], cmdArgs[1:]...)
	ctxCmd.Stdout = logFile
	ctxCmd.Stderr = logFile
	ctxCmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := ctxCmd.Start(); err != nil {
		log.Fatalf("Failed to start %v: %v", cmdArgs, err)
	}

	done := make(chan error, 1)
	go func() {
		done <- ctxCmd.Wait()
	}()

	select {
	case <-time.After(time.Duration(timeoutSec) * time.Second):
		pgid, _ := syscall.Getpgid(ctxCmd.Process.Pid)
		_ = syscall.Kill(-pgid, syscall.SIGTERM)
		time.Sleep(2 * time.Second)
		_ = syscall.Kill(-pgid, syscall.SIGKILL)

		fmt.Fprintf(logFile, "\n[TIMEOUT] exceeded %ds\n", timeoutSec)
		_ = logFile.Close() // Close before sanitizing
		sanitizeLogToFile(logPath)
		fmt.Printf("[FAIL] timeout %v. See %s\n", cmdArgs, logName)
		os.Exit(124)
	case err := <-done:
		_ = logFile.Close() // Close before sanitizing
		sanitizeLogToFile(logPath)
		if err != nil {
			if _, ok := err.(*exec.ExitError); ok {
				fmt.Printf("[FAIL] %v failed. See %s\n", cmdArgs, logName)
				os.Exit(failCode)
			}
		}
	}
}

func sanitizeLogToFile(path string) {
	root := resolveRepoRoot()
	if root == "" {
		return
	}
	content, err := os.ReadFile(path)
	if err != nil {
		return
	}
	newContent := strings.ReplaceAll(string(content), root, "<REPO_ROOT>")
	_ = os.WriteFile(path, []byte(newContent), 0644)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func runSelfVerify(dir string) {
	// Write self verify log, and include in checksums (already ensured by createManifestAndChecksums walking)
	logPath := filepath.Join(dir, fileSelfVerify)
	var buf bytes.Buffer
	buf.WriteString("self-verify: placeholder log\n")
	if err := os.WriteFile(logPath, buf.Bytes(), 0644); err != nil {
		log.Fatalf("[FATAL] write self verify log: %v", err)
	}
}
