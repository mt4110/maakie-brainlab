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
	rawDir := filepath.Join(dir, dirLogsRaw)
	portDir := filepath.Join(dir, dirLogsPortable)
	if err := os.MkdirAll(rawDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdir, rawDir, err)
	}
	if err := os.MkdirAll(portDir, 0755); err != nil {
		log.Fatalf(msgFatalMkdir, portDir, err)
	}

	rawLogPath := filepath.Join(rawDir, logName)
	rawLogFile, err := os.Create(rawLogPath)
	if err != nil {
		log.Fatal(err)
	}
	defer rawLogFile.Close()

	ctxCmd := exec.Command(cmdArgs[0], cmdArgs[1:]...)
	ctxCmd.Stdout = rawLogFile
	ctxCmd.Stderr = rawLogFile
	ctxCmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := ctxCmd.Start(); err != nil {
		log.Fatalf("Failed to start %v: %v", cmdArgs, err)
	}

	done := make(chan error, 1)
	go func() {
		done <- ctxCmd.Wait()
	}()

	var finalErr error
	var timeout bool

	select {
	case <-time.After(time.Duration(timeoutSec) * time.Second):
		timeout = true
		pgid, _ := syscall.Getpgid(ctxCmd.Process.Pid)
		_ = syscall.Kill(-pgid, syscall.SIGTERM)
		time.Sleep(2 * time.Second)
		_ = syscall.Kill(-pgid, syscall.SIGKILL)
		fmt.Fprintf(rawLogFile, "\n[TIMEOUT] exceeded %ds\n", timeoutSec)
	case err := <-done:
		finalErr = err
	}

	_ = rawLogFile.Close()

	// Post-processing: Portable Log and SHA256
	createPortableLog(rawLogPath, filepath.Join(portDir, logName))
	sha, _ := fileSha256(rawLogPath)
	_ = os.WriteFile(rawLogPath+".sha256", []byte(sha+"\n"), 0644)
	writePortableRules(portDir)

	if timeout {
		fmt.Printf("[FAIL] timeout %v. See %s/%s\n", cmdArgs, dirLogsRaw, logName)
		os.Exit(124)
	}

	if finalErr != nil {
		if _, ok := finalErr.(*exec.ExitError); ok {
			// S8-3.3: UX Polish for -mod=readonly
			if strings.Contains(cmdArgs[len(cmdArgs)-1], "-mod=readonly") || strings.Contains(cmdArgs[len(cmdArgs)-1], "ci") {
				rawBytes, _ := os.ReadFile(rawLogPath)
				if bytes.Contains(rawBytes, []byte("updates to go.mod needed")) || bytes.Contains(rawBytes, []byte("go.sum updates needed")) {
					fmt.Println("[HINT] S8 Audit Fail: go.mod/go.sum updates needed in -mod=readonly mode.")
					fmt.Println("[HINT] Run 'go mod tidy' and 'make test' locally, then commit changes.")
				}
			}
			fmt.Printf("[FAIL] %v failed. See %s/%s\n", cmdArgs, dirLogsRaw, logName)
			os.Exit(failCode)
		}
	}
}

func createPortableLog(src, dst string) {
	content, err := os.ReadFile(src)
	if err != nil {
		return
	}
	root := resolveRepoRoot()
	tmp := os.TempDir()
	// S8-4.3: Portable view (Suppress absolute paths)
	s := string(content)
	if root != "" {
		s = strings.ReplaceAll(s, root, "<REPO_ROOT>")
	}
	if tmp != "" {
		// os.TempDir() on mac often has a trailing slash or is a symlink.
		// We use a simple replacement for the base if possible.
		s = strings.ReplaceAll(s, tmp, "<TMPDIR>")
	}
	_ = os.WriteFile(dst, []byte(s), 0644)
}

func writePortableRules(dir string) {
	rules := `{
  "version": "v1",
  "rules": [
    {
      "type": "replace",
      "pattern": "<REPO_ROOT>",
      "description": "Redact absolute repository root path for portability"
    }
  ]
}
`
	_ = os.WriteFile(filepath.Join(dir, "rules-v1.json"), []byte(rules), 0644)
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
