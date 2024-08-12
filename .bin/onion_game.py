#!/usr/bin/env python

import argparse
import json
import random
import sys
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class Opt:
    limit: int


def main(args: Opt):
    score = 0
    for _ in range(args.limit):
        post = Post.random()
        print(f"{post.title}")
        is_onion = input_is_from_onion()
        match (is_onion, post.is_from_the_onion):
            case (True, True) | (False, False):
                score += 1
    print(f"Score: {score}/{args.limit}")


def input_is_from_onion() -> bool:
    while (
        answer := input(
            "Is this from The Onion? [y/n] ",
        )
        .strip()
        .lower()
    ):
        if answer not in "yesno":
            continue
        return answer in "yes"
    return False


@dataclass(frozen=True)
class Post:
    title: str
    subreddit: str
    is_from_the_onion: bool

    @staticmethod
    def from_dict(data):
        subreddit = data["subreddit"]
        return Post(
            subreddit=subreddit,
            title=data["title"],
            is_from_the_onion=subreddit == "TheOnion",
        )

    @staticmethod
    def random():
        subreddit = random.choice(["nottheonion", "TheOnion"])
        url = f"https://www.reddit.com/r/{subreddit}/random.json"
        headers = {"User-Agent": "script by u/erelde"}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            data = json.load(response)
        posts = data[0]["data"]["children"]
        return Post.from_dict(posts[0]["data"])


def parse_args(argv):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-l", "--limit", type=int, default=5)
    args = parser.parse_args(argv)
    return Opt(
        limit=args.limit,
    )


if __name__ == "__main__":
    sys.exit(main(parse_args(sys.argv[1:])))
