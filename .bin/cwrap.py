#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from typing import IO, TextIO, Tuple


@dataclass
class Opt:
    command: str
    num_lines: int


def main(args: Opt):
    proc = subprocess.Popen(
        args.command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        bufsize=1,
        universal_newlines=True,
    )

    q: Queue[Tuple[str, TextIO]] = Queue()

    t_stdout = Thread(target=enqueue_output, args=(proc.stdout, q, sys.stdout))
    t_stderr = Thread(target=enqueue_output, args=(proc.stderr, q, sys.stderr))
    t_stdout.daemon = True
    t_stderr.daemon = True
    t_stdout.start()
    t_stderr.start()

    start_time = time.time()
    output_lines: list[Tuple[str, TextIO]] = []
    hr = "-" * 12

    while True:
        elapsed = format_time(int(time.time() - start_time))

        while True:
            try:
                output_lines.append(q.get_nowait())
            except Empty:
                break

        print(f"\033[H\033[JElapsed Time: {elapsed}")
        print(hr)
        for line, source in output_lines[-args.num_lines :]:
            print(line, end="", file=source)
        output_lines = output_lines[-args.num_lines :]

        if proc.poll() is not None and q.empty():
            break

        time.sleep(0.01)

    elapsed = format_time(int(time.time() - start_time))
    print(hr)
    print(f"Elapsed Time: {elapsed}")
    return proc.returncode


def enqueue_output(out: IO[str], queue: Queue[Tuple[str, TextIO]], source: TextIO):
    for line in iter(out.readline, ""):
        queue.put((line, source))
    out.close()


def format_time(seconds: int):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{int(h)}h {int(m):02}m {int(s):02}s"
    elif m > 0:
        return f"{int(m)}m {int(s):02}s"
    else:
        return f"{int(s)}s"


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(
        description="""
        Run a command and display its output in a scrolling window.
        Doesn't particularly work well with outputs with lots of control characters.
        """
    )
    term = shutil.get_terminal_size((80, 20))
    parser.add_argument("command", help="The command to run")
    parser.add_argument(
        "-n",
        "--num-lines",
        type=int,
        default=max(term.lines - 40, 10),  # leave space for wrapping long lines
        help="Number of lines to display at a time",
    )
    args = parser.parse_args(argv)
    return Opt(command=args.command, num_lines=args.num_lines)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    sys.exit(main(args))
