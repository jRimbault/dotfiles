#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10.2"
# dependencies = [ "requests>=2.32.3" ]
# ///
import argparse
import random
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Queue

import requests


@dataclass(frozen=True)
class Opt:
    limit: int


@dataclass(frozen=True)
class Post:
    title: str
    subreddit: str
    is_onion: bool

    @staticmethod
    def from_dict(data):
        subreddit = data["subreddit"]
        return Post(
            subreddit=subreddit,
            title=data["title"],
            is_onion=subreddit == "TheOnion",
        )

    @staticmethod
    def random():
        subreddit = random.choice(["nottheonion", "TheOnion"])
        url = f"https://www.reddit.com/r/{subreddit}/random.json"
        data = requests.get(url).json()
        posts = data[0]["data"]["children"]
        return Post.from_dict(posts[0]["data"])


def main(args: Opt):
    score = 0
    with fetch_posts(args.limit) as posts:
        while post := posts.get():
            score += game_round(post)

    print(f"Score: {score}/{args.limit}")


def game_round(post: Post) -> int:
    print(post.title)
    match (ask_is_onion(), post.is_onion):
        case (True, True) | (False, False):
            print("Right")
            return 1
        case _:
            print("Wrong")
            return 0


def ask_is_onion() -> bool:
    prompt = "Is this from The Onion? [y/n] "
    while True:
        answer = input(prompt).lower()
        if answer == "":
            continue
        if answer not in "yesno":
            continue
        return answer in "yes"


def try_get_post():
    # Post.random() can fail because I don't quite know
    # the response's type, so sometimes the indexing will fail
    # no problem try again, it's only a small game
    while True:
        try:
            return Post.random()
        except:
            pass


@contextmanager
def fetch_posts(limit: int):
    def internal(q: Posts, limit: int):
        for _ in range(limit):
            q.queue.put(try_get_post())

    posts = Posts(Queue(), limit)
    thread = threading.Thread(target=internal, args=(posts, limit))
    thread.start()
    try:
        yield posts
    finally:
        thread.join()


@dataclass
class Posts:
    queue: Queue[Post]
    limit: int
    current: int = 0

    def get(self):
        if self.current == self.limit:
            return None
        self.current += 1
        return self.queue.get()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-l", "--limit", type=int, default=5)
    args = parser.parse_args(argv)
    return Opt(limit=args.limit)


if __name__ == "__main__":
    sys.exit(main(parse_args(sys.argv[1:])))
