package reviewpack

import (
	"log"
	"time"
)

func logPhase(name string) func() {
	start := time.Now()
	log.Printf("[PHASE_START] %s", name)
	return func() {
		log.Printf("[PHASE_END]   %s (%v)", name, time.Since(start))
	}
}
