package reviewpack

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// ContractV1 defines the schema for CONTRACT_v1 file.
type ContractV1 struct {
	ContractVersion           int      `json:"contract_version"`
	PackVersion               string   `json:"pack_version"`
	RequiredPaths             []string `json:"required_paths"`
	PortableLogRequiresSha256 bool     `json:"portable_log_requires_sha256"`
}

func writeContractV1(dir string) {
	contract := ContractV1{
		ContractVersion: 1,
		PackVersion:     "2",
		RequiredPaths: []string{
			filePackVersion,
			fileContractV1,
			dirLogsPortable,
			filepath.Join(dirLogsPortable, "rules-v1.json"),
		},
		PortableLogRequiresSha256: true,
	}

	data, err := json.MarshalIndent(contract, "", "  ")
	if err != nil {
		logFatal(fmt.Sprintf("JSON marshal CONTRACT_v1: %v", err))
	}

	path := filepath.Join(dir, fileContractV1)
	// Ensure trailing newline
	body := append(data, '\n')
	if err := os.WriteFile(path, body, 0644); err != nil {
		logFatal(fmt.Sprintf(msgFatalWrite, path, err))
	}
}

// verifyContractV1 enforces the AI Contract v1 specifications.
func verifyContractV1(root string) {
	// 1. CONTRACT_v1 existence and valid JSON
	contractPath := filepath.Join(root, fileContractV1)
	data, err := os.ReadFile(contractPath)
	if err != nil {
		logFatal(fmt.Sprintf("contract_v1: missing or unreadable: %s", contractPath))
	}

	var contract ContractV1
	if err := json.Unmarshal(data, &contract); err != nil {
		logFatal(fmt.Sprintf("contract_v1: invalid JSON: %v", err))
	}

	if contract.ContractVersion != 1 {
		logFatal(fmt.Sprintf("contract_v1: unsupported contract version: %d", contract.ContractVersion))
	}

	// 2. dir logs/portable and rules-v1.json
	portDir := filepath.Join(root, dirLogsPortable)
	if st, err := os.Stat(portDir); err != nil || !st.IsDir() {
		logFatal(fmt.Sprintf("contract_v1: missing required directory: %s", dirLogsPortable))
	}

	rulesPath := filepath.Join(portDir, "rules-v1.json")
	rulesData, err := os.ReadFile(rulesPath)
	if err != nil {
		logFatal(fmt.Sprintf("contract_v1: missing required path: %s", rulesPath))
	}
	var rules interface{}
	if err := json.Unmarshal(rulesData, &rules); err != nil {
		logFatal(fmt.Sprintf("contract_v1: rules-v1.json is not valid JSON: %v", err))
	}

	// 3. At least one *.log in logs/portable/
	entries, err := os.ReadDir(portDir)
	if err != nil {
		logFatal(fmt.Sprintf("contract_v1: readdir %s: %v", portDir, err))
	}
	hasLog := false
	for _, e := range entries {
		if !e.IsDir() && filepath.Ext(e.Name()) == ".log" {
			hasLog = true
			// 4. Each *.log must have *.log.sha256
			shaPath := filepath.Join(portDir, e.Name()+".sha256")
			if _, err := os.Stat(shaPath); err != nil {
				logFatal(fmt.Sprintf("contract_v1: missing sidecar for log: %s", shaPath))
			}
		}
	}
	if !hasLog {
		logFatal(fmt.Sprintf("contract_v1: no portable logs found in %s", dirLogsPortable))
	}
}

// logFatal is a helper to ensure we use the same message format if we decide to change it.
func logFatal(msg string) {
	fmt.Fprintf(os.Stderr, "[FAIL] %s\n", msg)
	os.Exit(1)
}
