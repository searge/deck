// Package display provides terminal output helpers using Lipgloss.
// All functions are pure: they return strings, never print directly.
// Callers decide when and where to print.
package display

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Semantic terminal colors. Uses default terminal palette so themes
// (Nord, Gruvbox, etc.) are respected automatically.
var (
	colorSuccess = lipgloss.Color("2") // green
	colorError   = lipgloss.Color("1") // red
	colorWarn    = lipgloss.Color("3") // yellow
	colorInfo    = lipgloss.Color("6") // cyan
	colorDim     = lipgloss.Color("8") // bright_black
)

// Exported styles for use in other packages.
var (
	StyleHeader  = lipgloss.NewStyle().Bold(true).Foreground(colorInfo)
	StyleSuccess = lipgloss.NewStyle().Bold(true).Foreground(colorSuccess)
	StyleError   = lipgloss.NewStyle().Bold(true).Foreground(colorError)
	StyleWarn    = lipgloss.NewStyle().Foreground(colorWarn)
	StyleDim     = lipgloss.NewStyle().Foreground(colorDim)
)

const lineWidth = 64

// Header renders a section header with thin separator lines.
// Pure function: returns a string.
func Header(title string) string {
	line := StyleHeader.Render(strings.Repeat("─", lineWidth))
	return fmt.Sprintf("%s\n  %s\n%s", line, StyleHeader.Render(title), line)
}

// Success renders a COMPLETE status message.
// Pure function: returns a string.
func Success(message string) string {
	return fmt.Sprintf("%s: %s", StyleSuccess.Render("COMPLETE"), message)
}

// Error renders an ERROR status message.
// Pure function: returns a string.
func Error(message string) string {
	return fmt.Sprintf("%s: %s", StyleError.Render("ERROR"), message)
}

// Warn renders a WARNING status message.
// Pure function: returns a string.
func Warn(message string) string {
	return fmt.Sprintf("%s: %s", StyleWarn.Render("WARNING"), message)
}

// Info renders an INFO status message.
// Pure function: returns a string.
func Info(message string) string {
	return fmt.Sprintf("%s: %s", StyleDim.Render("INFO"), message)
}

// KeyValue renders a key-value pair, left-aligned with fixed key width.
// Pure function: returns a string.
func KeyValue(key, value string) string {
	return fmt.Sprintf("  %-20s: %s", key, value)
}
