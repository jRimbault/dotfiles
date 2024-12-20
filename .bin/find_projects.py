#!/usr/bin/env python

r"""
Both of these:

```
find . -type d \( -name ".git" -o -name ".hg" \) -print0 | xargs -0 dirname
fd -u --type d '\.(git|hg)$' . | xargs -n1 dirname
```

perform a lot worse than this single purpose script
"""


import os
import sys
from pathlib import Path


def search_projects(path: Path):
    for root, dirnames, _ in os.walk(path):
        if ".git" in dirnames or ".hg" in dirnames:
            for directory in list(dirnames):
                dirnames.remove(directory)
            yield Path(root).relative_to(path)

try:
    base = Path(sys.argv[1])
except IndexError:
    base = Path.cwd()

for project in search_projects(base):
    print(project)
