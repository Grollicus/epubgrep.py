#!/usr/bin/env python3

import os
import re
import stat
import zipfile
from io import BytesIO
from signal import signal, SIGQUIT
from argparse import ArgumentParser


class EpubGrep(object):
    def __init__(self, pattern, min_matches, ignore_case=False):
        self.already_visited = set([])
        if type(pattern) is str:
            pattern = bytes(pattern, 'utf-8')
        if type(pattern) is bytes:
            pattern = re.compile(pattern, re.I if ignore_case else 0)
        self.pattern = pattern
        self.min_matches = min_matches
        self.status = 'not started'

    def iterfiles(self, path):
        path = os.path.realpath(path)
        if path in self.already_visited:
            return
        self.already_visited.add(path)
        self.status = path
        mode = os.stat(path).st_mode
        if stat.S_ISDIR(mode):
            for sp in os.listdir(path):
                for f in self.iterfiles(os.path.join(path, sp)):
                    yield f
        elif stat.S_ISREG(mode):
            with open(path, mode='rb') as f:
                c = f.read()
            if len(c) < 4 or not c.startswith(b'PK\x03\x04'):
                yield (path, c)
                return
            try:
                b = BytesIO(c)
                with zipfile.ZipFile(b, compression=zipfile.ZIP_DEFLATED, mode='r') as z:
                    for name in z.namelist():
                        yield (b'%s:%s' % (path, bytes(name, 'utf-8')), z.read(name))
                return
            except Exception as e:
                print("Failed to open %s: %s" % (path, e))
                yield (path, c)

    def searchin(self, path):
        if type(path) is str:
            path = bytes(path, 'utf-8')
        for (f, c) in self.iterfiles(path):
            n = len(self.pattern.findall(c))
            if n >= self.min_matches:
                print("%s: %d" % (f, n))
        self.status = 'finished'


if __name__ == "__main__":

    parser = ArgumentParser(prog='epubgrep', description='Grep for regex in epub files')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-Insensitive matching')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show pattern before beginning to search')
    parser.add_argument('-m', '--min-matches', action='store', type=int, default=1, help='Minimum number of matches per file')
    parser.add_argument('pattern')
    parser.add_argument('file', nargs='+')
    args = parser.parse_args()

    if args.verbose:
        print("Pattern:", args.pattern)

    grep = EpubGrep(args.pattern, args.min_matches, args.ignore_case)

    def printstatus(signum, frame):
        print("Current Status: %s" % repr(grep.status))
    signal(SIGQUIT, printstatus)

    for path in args.file:
        grep.searchin(path)
