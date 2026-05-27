#!/usr/bin/env bash

dir="${1:-$PWD}"
git -C "$dir" fetch --quiet & 2>&1 > /dev/null
branch="$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || echo detached)"
echo -e "\033[1;36m$(basename "$dir")\033[0m $branch"

git -c color.log=always --no-pager -C "$dir" log -1 \
    --pretty=format:'%C(auto)%h%C(reset)  %s  %C(dim)%n%cr by %an%n'

git -c color.status=always -C "$dir" status -s

readmes=(README.rst README README.md)

for file in "${readmes[@]}"; do
    if [[ -f "$dir/$file" ]]; then
        echo
        bat --plain -f --line-range :20 "$dir/$file"
    fi
done
