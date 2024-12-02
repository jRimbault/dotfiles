#!/usr/bin/env python3
# pyright: strict

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

assert sys.version_info >= (3, 11), "Must use python >=3.11"

@dataclass
class Options:
    file: Path
    algorithm: str


def main(options: Options) -> None:
    with options.file.open("rb") as f:
        hash_value = hashlib.file_digest(f, options.algorithm).hexdigest()
    print(f"{hash_value} {options.file.absolute()}")


def parse_args(argv: list[str]) -> Options:
    parser = argparse.ArgumentParser(description="File hashing utility.")
    parser.add_argument(
        "algorithm",
        choices=sorted(hashlib.algorithms_guaranteed),
        help="Hashing algorithm to use (guaranteed to be available).",
    )
    parser.add_argument("file", type=Path, help="Path to the file to hash.")
    args = parser.parse_args(argv)
    return Options(file=args.file, algorithm=args.algorithm)


if __name__ == "__main__":
    sys.exit(main(parse_args(sys.argv[1:])))
