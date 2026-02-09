package main

import (
	"os"

	"reviewpack/internal/reviewpack"
)

func main() {
	os.Exit(reviewpack.Run(os.Args))
}
