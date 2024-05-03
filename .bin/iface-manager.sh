#!/usr/bin/env bash

kind="${1:-all}"
task="${2:-show}"
if [ "$kind" = "PHYS" ]; then
  task="show"
fi

main() {
  all_interfaces | filter | action
}

action() {
  while IFS=$'\n' read -r iface; do
    case "$task" in
      show) echo "$iface";;
      delete)
        set -x
        sudo ip link delete "$iface"
        set +x
        ;;
    esac
  done
}

all_interfaces() {
  ip link show |
    grep -E '^([0-9]+):' |
    cut -d: -f 2 |
    tr -d ' '
}

filter() {
  while IFS=$'\n' read -r iface; do
    if test -n "$iface" && ip addr show dev "$iface" >/dev/null 2>&1; then
      if test -e "/sys/class/net/$iface/device"; then
        if [ "$kind" = "PHYS" ] || [ "$kind" = "all" ]; then
          echo "$iface"
        fi
      else
        if [ "$kind" = "all" ] || [ "$kind" = "VIRT" ] && [ "$iface" != "lo" ]; then
          echo "$iface"
        fi
      fi
    fi
  done
}

main
