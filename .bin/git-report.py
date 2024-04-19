#!/usr/bin/env python3

import argparse
import subprocess
import sys
from contextlib import contextmanager

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable):
        def report(i):
            print(f"{i+1:>{formatter}}/{total}", file=sys.stderr, end="\r")

        total = len(iterable)
        formatter = len(str(total))
        for i, el in enumerate(iterable):
            yield el
            report(i)


def main(args):
    with out_file(args.output) as out:
        print_csv(lambda s: print(s, file=out))


def print_csv(printer: callable):
    printer("files;insertions;deletions;author;branch")
    for stats in collect_stats(git_authors()):
        printer(stats)


def check_output(command):
    return subprocess.check_output(command).decode("utf-8", "ignore")


def collect_stats(authors):
    for author in tqdm(authors):
        try:
            yield check_output(("git-insertions", author)).strip()
        except subprocess.CalledProcessError:
            continue
    print("Done.", file=sys.stderr)


def git_authors():
    print("Fetching list of committers...", file=sys.stderr)
    return check_output(("git-authors")).splitlines()


@contextmanager
def out_file(file):
    try:
        out = open(file, "w", buffering=1)
        yield out
    except TypeError:
        yield sys.stdout
    finally:
        if "out" in locals():
            out.close()


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", help="Output file")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        main(parse_args(sys.argv[1:]))
    except KeyboardInterrupt:
        print()
