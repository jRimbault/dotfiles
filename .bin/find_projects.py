#!/usr/bin/env python

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
# bug and performance fixes to rglob will come in python 3.12 and 3.13
# as well as the `walk_up=True` option for `relative_to`
# for now I'll use the `os.walk` function
# mercurial = (p.parent.relative_to(base) for p in base.rglob("**/.hg"))
# git = (p.parent.relative_to(base) for p in base.rglob("**/.git"))
# for project in itertools.chain(mercurial, git):
for project in search_projects(base):
    print(project)
