#!/usr/bin/env python

r"""
Both of these:

```sh
find . -type d \( -name ".git" -o -name ".hg" \) -print0 | xargs -0 dirname
fd -u --type d '\.(git|hg)$' . | xargs -n1 dirname
```

perform a lot worse than this single purpose script

```sh
hyperfine -w 10 \
    'find_projects.py ~/Documents' \
    'find ~/Documents -type d \( -name ".git" -o -name ".hg" \) -print0 | xargs -0 dirname'\
    "fd -u --type d '\.(git|hg)$' ~/Documents | xargs -n1 dirname"
```sh
"""


import os
import sys
from pathlib import Path
import threading
from queue import Queue


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

try:
    mode = sys.argv[2]
except IndexError:
    mode = "single"


projects: Queue[Path | None] = Queue()

def producer(queue: Queue[Path | None]):
    for project in search_projects(base):
        queue.put(project)
    queue.put(None)  # Sentinel to signal the consumer to stop

def consumer(queue: Queue[Path | None], batch_size=50):
    buffer: list[Path] = []
    while True:
        item = queue.get()
        if item is None:
            if buffer:
                for p in buffer:
                    print(p)
            break
        buffer.append(item)
        if len(buffer) >= batch_size:
            for p in buffer:
                print(p)
            buffer.clear()


match mode:
    case "single":
        for project in search_projects(base):
            print(project)
    case "single-batch":
        for project in search_projects(base):
            print(project)
    case "multi":
        producer_thread = threading.Thread(target=producer, args=(projects,))
        producer_thread.start()
        while project := projects.get():
            print(project)
        producer_thread.join()
    case "multi-batch":
        producer_thread = threading.Thread(target=producer, args=(projects,))
        producer_thread.start()
        consumer(projects)
        producer_thread.join()



