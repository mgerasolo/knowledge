#!/bin/bash
# Tracker Module Error Handler
# Provides human-friendly errors and herding integration

# Source this file in scripts that need error handling:
#   source "$(dirname "$0")/../lib/error-handler.sh"

# Configuration
HERDING_SCRIPT="/mnt/foundry_resources/scripts/herd.sh"
TRACKER_LOG_FILE="${TRACKER_LOG_FILE:-/tmp/tracker-$(date +%Y%m%d).log}"
TRACKER_AUTO_REPORT="${TRACKER_AUTO_REPORT:-false}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Error codes and friendly messages
declare -A ERROR_MESSAGES=(
    ["BMAD_NOT_FOUND"]="BMAD is not installed in this project. Run '/bmad install' first."
    ["CONFIG_MISSING"]="Oscar configuration file not found. Run '/oscar:setup' to create one."
    ["CONFIG_INVALID"]="Oscar configuration file is invalid. Check YAML syntax."
    ["SIDECAR_NOT_FOUND"]="Oscar sidecar directory not found. Run '/oscar:setup' to recreate."
    ["SIDECAR_NOT_WRITABLE"]="Cannot write to Oscar's sidecar directory. Check permissions on _bmad/_memory/"
    ["ADAPTER_FAILED"]="Could not connect to tracking system. Check your config in /oscar:config"
    ["ADAPTER_NOT_FOUND"]="Tracking adapter not found. Supported: github, linear, bmad-artifacts"
    ["GATE_SCRIPT_FAILED"]="Gate check script failed. Review the error above and fix the issue."
    ["GATE_NOT_FOUND"]="Gate script not found. Check _bmad/tracker/config/gates/"
    ["MANIFEST_UPDATE_FAILED"]="Could not update BMAD manifest. Check write permissions."
    ["VERSION_MISMATCH"]="Installed version doesn't match expected version. Run /oscar:upgrade"
    ["WORKFLOW_NOT_FOUND"]="Workflow not found. Check _bmad/tracker/workflows/"
    ["AGENT_NOT_FOUND"]="Oscar agent file not found. Tracker module may be corrupted. Reinstall."
    ["PERMISSION_DENIED"]="Permission denied. Check file/directory permissions."
    ["NETWORK_ERROR"]="Network error connecting to tracking system. Check connectivity."
    ["UNKNOWN_ERROR"]="An unexpected error occurred. Check the log file for details."
)

# Log error with context
log_error() {
    local code="$1"
    local message="$2"
    local context="${3:-}"
    local timestamp=$(date -Is)

    # Human-friendly output
    echo ""
    echo -e "${RED}Error: $message${NC}"
    echo ""

    # Detailed log
    echo "[$timestamp] ERROR $code: $message" >> "$TRACKER_LOG_FILE"
    [[ -n "$context" ]] && echo "   Context: $context" >> "$TRACKER_LOG_FILE"
}

# Log warning (non-fatal)
log_warning() {
    local message="$1"
    local timestamp=$(date -Is)

    echo -e "${YELLOW}Warning: $message${NC}"
    echo "[$timestamp] WARNING: $message" >> "$TRACKER_LOG_FILE"
}

# Log info
log_info() {
    local message="$1"
    local timestamp=$(date -Is)

    echo -e "${BLUE}$message${NC}"
    echo "[$timestamp] INFO: $message" >> "$TRACKER_LOG_FILE"
}

# Log success
log_success() {
    local message="$1"
    local timestamp=$(date -Is)

    echo -e "${GREEN}$message${NC}"
    echo "[$timestamp] SUCCESS: $message" >> "$TRACKER_LOG_FILE"
}

# Report error to herding
report_to_herding() {
    local code="$1"
    local message="$2"

    if [[ -x "$HERDING_SCRIPT" ]]; then
        cat << EOF | "$HERDING_SCRIPT" new tracker --stdin 2>/dev/null || true
Error Code: $code
Message: $message
Timestamp: $(date -Is)
Project: ${PWD##*/}
User: ${USER}
Host: $(hostname)
EOF
        echo -e "${BLUE}Error reported to herding feedback system${NC}"
    fi
}

# Get friendly message for error code
get_error_message() {
    local code="$1"
    echo "${ERROR_MESSAGES[$code]:-Unknown error: $code}"
}

# Handle error with full context
handle_error() {
    local code="$1"
    local details="${2:-}"
    local message=$(get_error_message "$code")

    log_error "$code" "$message" "$details"

    echo -e "${BLUE}How to fix:${NC}"
    case "$code" in
        "BMAD_NOT_FOUND")
            echo "   1. Run: /bmad install"
            echo "   2. Then retry your command"
            ;;
        "CONFIG_MISSING"|"CONFIG_INVALID")
            echo "   1. Run: /oscar:setup"
            echo "   2. Follow the interactive prompts"
            ;;
        "SIDECAR_NOT_FOUND"|"SIDECAR_NOT_WRITABLE")
            echo "   1. Check that _bmad/_memory/ exists"
            echo "   2. Ensure you have write permissions"
            echo "   3. Run: chmod -R u+w _bmad/_memory/"
            echo "   4. Or reinstall: /oscar:setup"
            ;;
        "ADAPTER_FAILED"|"ADAPTER_NOT_FOUND")
            echo "   1. Run: /oscar:config to review settings"
            echo "   2. Verify your tracking system credentials"
            echo "   3. Check network connectivity"
            ;;
        "GATE_SCRIPT_FAILED"|"GATE_NOT_FOUND")
            echo "   1. Review the gate script output above"
            echo "   2. Fix any test failures or missing files"
            echo "   3. Run: /oscar:gate to retry"
            ;;
        "VERSION_MISMATCH")
            echo "   1. Run: /oscar:upgrade to update the module"
            echo "   2. Review any breaking changes"
            ;;
        "WORKFLOW_NOT_FOUND"|"AGENT_NOT_FOUND")
            echo "   1. The tracker module may be corrupted"
            echo "   2. Run: /mnt/foundry_resources/protocols/tracker/install.sh"
            ;;
        "PERMISSION_DENIED")
            echo "   1. Check file ownership: ls -la"
            echo "   2. Fix permissions: chmod u+rw <file>"
            echo "   3. Or run with appropriate privileges"
            ;;
        "NETWORK_ERROR")
            echo "   1. Check internet connectivity"
            echo "   2. Verify tracking system URL in config"
            echo "   3. Check if VPN is required"
            ;;
        *)
            echo "   1. Check the log file: $TRACKER_LOG_FILE"
            echo "   2. Report to herding if issue persists"
            ;;
    esac

    echo ""
    echo -e "${BLUE}Log file: $TRACKER_LOG_FILE${NC}"

    # Auto-report to herding for unexpected errors
    if [[ "$TRACKER_AUTO_REPORT" == "true" ]] || [[ "$code" == "UNKNOWN_ERROR" ]]; then
        report_to_herding "$code" "$message"
    fi
}

# Fatal error - logs, shows fix, optionally reports, then exits
fatal_error() {
    local code="$1"
    local details="${2:-}"
    handle_error "$code" "$details"
    exit 1
}

# Check if file exists and is readable
check_file_readable() {
    local file="$1"
    local error_code="${2:-PERMISSION_DENIED}"
    if [[ ! -f "$file" ]]; then
        return 1
    fi
    if [[ ! -r "$file" ]]; then
        handle_error "$error_code" "File not readable: $file"
        return 1
    fi
    return 0
}

# Check if directory exists and is writable
check_dir_writable() {
    local dir="$1"
    local error_code="${2:-PERMISSION_DENIED}"
    if [[ ! -d "$dir" ]]; then
        return 1
    fi
    if [[ ! -w "$dir" ]]; then
        handle_error "$error_code" "Directory not writable: $dir"
        return 1
    fi
    return 0
}

# Validate YAML file
validate_yaml() {
    local file="$1"
    if command -v yq &> /dev/null; then
        if ! yq eval '.' "$file" > /dev/null 2>&1; then
            return 1
        fi
    fi
    return 0
}
