// Package config provides application configuration.
// All Config values are immutable after construction.
package config

import (
	"fmt"
	"os"
)

// Config holds application configuration.
// Treat as immutable: construct once, pass by value or pointer.
type Config struct {
	LogLevel string
	Debug    bool
}

// Default returns a Config with sensible defaults.
// Pure function: no side effects.
func Default() Config {
	return Config{
		LogLevel: "info",
		Debug:    false,
	}
}

// FromEnv reads configuration from environment variables.
// Returns a new Config; does not mutate anything.
func FromEnv() (Config, error) {
	cfg := Default()

	if level := os.Getenv("LOG_LEVEL"); level != "" {
		if err := validateLogLevel(level); err != nil {
			return Config{}, fmt.Errorf("invalid LOG_LEVEL: %w", err)
		}
		cfg.LogLevel = level
	}

	cfg.Debug = os.Getenv("DEBUG") == "true"

	return cfg, nil
}

// validateLogLevel checks whether the value is an accepted log level.
// Pure function.
func validateLogLevel(level string) error {
	valid := map[string]struct{}{
		"debug": {}, "info": {}, "warn": {}, "error": {},
	}
	if _, ok := valid[level]; !ok {
		return fmt.Errorf("%q is not valid; choose: debug, info, warn, error", level)
	}
	return nil
}
