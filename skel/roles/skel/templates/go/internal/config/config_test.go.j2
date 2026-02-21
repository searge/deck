package config

import (
	"testing"
)

func TestDefault(t *testing.T) {
	cfg := Default()
	if cfg.LogLevel != "info" {
		t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, "info")
	}
	if cfg.Debug {
		t.Error("Debug should be false by default")
	}
}

func TestFromEnv(t *testing.T) {
	tests := []struct {
		name    string
		env     map[string]string
		wantErr bool
		wantLog string
		wantDbg bool
	}{
		{
			name:    "defaults when no env",
			env:     map[string]string{},
			wantLog: "info",
		},
		{
			name:    "reads LOG_LEVEL",
			env:     map[string]string{"LOG_LEVEL": "debug"},
			wantLog: "debug",
		},
		{
			name:    "reads DEBUG",
			env:     map[string]string{"DEBUG": "true"},
			wantLog: "info",
			wantDbg: true,
		},
		{
			name:    "invalid LOG_LEVEL",
			env:     map[string]string{"LOG_LEVEL": "verbose"},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			for k, v := range tt.env {
				t.Setenv(k, v)
			}

			cfg, err := FromEnv()

			if (err != nil) != tt.wantErr {
				t.Fatalf("FromEnv() error = %v, wantErr %v", err, tt.wantErr)
			}
			if tt.wantErr {
				return
			}
			if tt.wantLog != "" && cfg.LogLevel != tt.wantLog {
				t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, tt.wantLog)
			}
			if cfg.Debug != tt.wantDbg {
				t.Errorf("Debug = %v, want %v", cfg.Debug, tt.wantDbg)
			}
		})
	}
}
