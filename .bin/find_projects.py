#!/usr/bin/env python

r"""
Both of these:

```sh
find . -type d \( -name ".git" -o -name ".hg" \) -print0 | xargs -0 dirname
fd -u --type d '\.(git|hg)$' . | xargs -n1 dirname
```

perform a lot worse than this single purpose script.

Benchmark script:

```sh
hyperfine -w 10 \
    'find_projects.py ~/Documents' \
    'find ~/Documents -type d \( -name ".git" -o -name ".hg" \) -print0 | xargs -0 dirname'\
    "fd -u --type d '\.(git|hg)$' ~/Documents | xargs -n1 dirname"
```
"""


import os
import sys
from pathlib import Path


def search_projects(path: Path):
    for root, dirnames, _ in os.walk(path):
        if not any(".git" == name or ".hg" == name for name in dirnames):
            continue
        dirnames.clear()
        yield Path(root).relative_to(path)

try:
    base = Path(sys.argv[1])
except IndexError:
    base = Path.cwd()

for project in search_projects(base):
    print(project)
