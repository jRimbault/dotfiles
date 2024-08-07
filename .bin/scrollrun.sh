#!/usr/bin/env bash

# Default number of lines to display
NUM_LINES=10

main() {
    START_TIME=$(date +%s)
    while read -r line </dev/stdin; do
        # Calculate elapsed time
        NOW=$(date +%s)
        ELAPSED_TIME=$((NOW - START_TIME))
        echo "$line" >>"$BUFFER"

        clear
        echo "Elapsed time: $(format_elapsed_time $ELAPSED_TIME)"
        echo "------------"
        tail -n "$NUM_LINES" "$BUFFER"
    done
    cleanup
}

# Function to format elapsed time
format_elapsed_time() {
    local SECONDS=$1
    local HOURS=$((SECONDS / 3600))
    local MINUTES=$(((SECONDS % 3600) / 60))
    local SECONDS=$((SECONDS % 60))
    if [ $HOURS -gt 0 ]; then
        printf "%dh %02dm %02ds" $HOURS $MINUTES $SECONDS
    elif [ $MINUTES -gt 0 ]; then
        printf "%dm %02ds" $MINUTES $SECONDS
    else
        printf "%ds" $SECONDS
    fi
}

cleanup() {
    rm "$BUFFER"
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
    # Parse arguments
    while getopts "n:" opt; do
        case $opt in
        n) NUM_LINES=$OPTARG ;;
        *)
            echo "Usage: $0 [-n num_lines]"
            exit 1
            ;;
        esac
    done
    BUFFER="$(mktemp -t scrollrun.XXXXXXXX)"
    trap cleanup SIGINT SIGTERM
    main "$@"
fi
