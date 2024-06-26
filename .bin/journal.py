#!/usr/bin/env python3

"""journal

Use a git repository as a journal.
Each commit is a journal entry.
The actual repository could contain no files.

This script mostly only exists to be able to write to
the journal from anywhere and add some semantic aliases like:
  journal write
  journal entries
  journal read

All of those can be completed by any valid git options
for the command it's aliasing:
  journal write -m "a quick passing thought"
  journal read --reverse --after=2017 --before=2018-02-03
"""

import argparse
import os
import subprocess
import sys
import textwrap


def main(args, argv):
    return args.action(args, argv)


def journal(func):
    def inner(args, argv):
        for command in func(args, argv):
            process = subprocess.run(command, cwd=args.repository, check=False)
        return process.returncode

    return inner


@journal
def read(args, argv):
    if args.ref is None:
        yield ["git", "log"] + argv
        return
    if args.ref == "last":
        yield ["git", "show", "--shortstat", "-1"]
        return
    output = subprocess.check_output(
        ["git", "rev-list", "--all"], cwd=args.repository, text=True
    )
    for line in output.splitlines():
        if args.ref in line:
            yield ["git", "show", "--shortstat", args.ref] + argv
            return
    output = subprocess.check_output(
        ["git", "log", "--grep", args.ref, "--format=%H"],
        cwd=args.repository,
        text=True,
    )
    if output.strip() == "":
        yield ["false"]
        return
    first = output.splitlines()[0]
    yield ["git", "show", "--shortstat", first] + argv


@journal
def entries(args, argv):
    yield [
        "git",
        "log",
        "--date=short",
        "--format=%C(red)%h%Creset %C(green)%ad%Creset %s",
    ] + argv


@journal
def nav_entries(args, argv):
    yield ["git-nav-log"] + argv


@journal
def write(args, argv):
    yield ["git", "commit", "--allow-empty"] + argv


@journal
def backup(args, argv):
    yield ["git", "pull", "-r"]
    yield ["git", "push"] + argv
    yield ["git", "status"]


def parse_args(argv):
    def program_is_available(program):
        def is_exe(path):
            return os.path.isfile(path) and os.access(path, os.X_OK)

        return any(
            is_exe(os.path.join(path, program))
            for path in os.environ["PATH"].split(os.pathsep)
        )

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            Script meant to interact with a git repository used as a journal.

            Set the environment variable 'JOURNAL_REPO' to a path pointing
            to a git repository which will be used as the journal.
            """
        ),
        epilog=textwrap.dedent(
            """
            usage examples:
              journal entries --after=2019
              journal read <shasum>
              journal write -m "a quick passing thought"
              journal read --reverse --after=2017 --before=2018-02-03
            """
        ),
    )
    parser.set_defaults(action=lambda _, __: parser.print_help())
    journal_repo = os.environ.get("JOURNAL_REPO")
    parser.add_argument(
        "-r",
        "--repository",
        metavar="path",
        default=journal_repo,
        required=journal_repo is None,
        help="override the JOURNAL_REPO environment variable",
    )
    subparsers = parser.add_subparsers(
        description="can be completed by any valid git options for the command it's aliasing",
    )

    def add_subcommand(name, *, help_text, aliases, action):
        sub = subparsers.add_parser(name, help=help_text, aliases=aliases)
        sub.set_defaults(action=action)
        return sub

    add_subcommand(
        "read",
        help_text="use to read the whole journal [log|show]",
        aliases=["r"],
        action=read,
    ).add_argument("ref", help="commit reference", nargs="?")
    add_subcommand(
        "entries",
        help_text="list the journal entries [log]",
        aliases=["e"],
        action=entries,
    )
    # depends on my other script `git-nav-log` and `fzf`
    if all(map(program_is_available, ["git-nav-log", "fzf"])):
        add_subcommand(
            "nav-entries",
            help_text="navigate the journal entries [git-nav-log]",
            aliases=["n"],
            action=nav_entries,
        )
    add_subcommand(
        "write", help_text="write a new entry [commit]", aliases=["w"], action=write
    )
    add_subcommand(
        "backup", help_text="sync the new entries", aliases=["b"], action=backup
    )
    args, argv = parser.parse_known_args(argv)
    if args.repository is None:
        args.action = lambda _, __: parser.print_help()
    return args, argv


if __name__ == "__main__":
    sys.exit(main(*parse_args(sys.argv[1:])))
