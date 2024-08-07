#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from typing import IO, TextIO, Tuple


@dataclass
class Opt:
    command: str
    num_lines: int


HR = "-" * 12


def main(args: Opt):
    child_lines: Queue[Tuple[str, TextIO]] = Queue()
    with (
        subprocess.Popen(
            args.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            bufsize=1,
            universal_newlines=True,
        ) as proc,
        consumer(proc.stdout, child_lines, sys.stdout),
        consumer(proc.stderr, child_lines, sys.stdout),
    ):
        start_time = time.time()
        output_lines: list[Tuple[str, TextIO]] = []

        while True:
            elapsed = format_time(int(time.time() - start_time))

            while True:
                try:
                    output_lines.append(child_lines.get_nowait())
                except Empty:
                    break

            print(f"\033[H\033[JElapsed time: {elapsed}")
            print(HR)
            for line, source in output_lines[-args.num_lines :]:
                print(line, end="", file=source)
            output_lines = output_lines[-args.num_lines :]

            if proc.poll() is not None and child_lines.empty():
                break

            time.sleep(0.01)

        elapsed = format_time(int(time.time() - start_time))
        print(HR)
        print(f"Finished in: {elapsed}")
        return proc.returncode


@contextmanager
def consumer(reader: IO[str] | None, queue: Queue[Tuple[str, TextIO]], source: TextIO):
    if reader is None:
        raise Exception("no IO to read")
    child = Thread(target=enqueue_output, args=(reader, queue, source))
    child.start()
    try:
        yield None
    finally:
        child.join()


def enqueue_output(reader: IO[str], queue: Queue[Tuple[str, TextIO]], source: TextIO):
    for line in iter(reader.readline, ""):
        queue.put((line, source))
    reader.close()


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
