#!/usr/bin/env python3

import os
import re
import stat
import zipfile
from io import BytesIO


class EpubGrep(object):
    def __init__(self, pattern):
        self.already_visited = set([])
        if type(pattern) is str:
            pattern = bytes(pattern, 'utf-8')
        self._pattern = pattern
        if type(pattern) is bytes:
            pattern = re.compile(pattern)
        self.pattern = pattern
        self.min_matches = 1
        self.ignore_case = False
        self.max_size = 10*1024*1024
        self.status = 'not started'

    def setMinMatches(self, min):
        self.min_matches = min

    def setIgnoreCase(self, ignore):
        self.ignore_case = ignore
        if type(self._pattern) is bytes:
            self.pattern = re.compile(self._pattern, re.I if ignore else 0)

    def setMaxSize(self, size):
        self.max_size = size

    def iterfiles(self, path):
        path = os.path.realpath(path)
        if path in self.already_visited:
            return
        self.already_visited.add(path)
        self.status = path
        st = os.stat(path)
        mode = st.st_mode
        if stat.S_ISDIR(mode):
            for sp in os.listdir(path):
                for f in self.iterfiles(os.path.join(path, sp)):
                    yield f
        elif stat.S_ISREG(mode):
            if st.st_size > self.max_size:
                return
            with open(path, mode='rb') as f:
                c = f.read()
            if len(c) < 4 or not c.startswith(b'PK\x03\x04'):
                yield (path, c)
                return
            try:
                b = BytesIO(c)
                with zipfile.ZipFile(b, compression=zipfile.ZIP_DEFLATED, mode='r') as z:
                    for member in z.infolist():
                        if member.file_size > self.max_size:
                            continue
                        yield (b'%s:%s' % (path, bytes(member.filename, 'utf-8')), z.read(member.filename))
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


def filesize(size_str):
    m = re.match('(\d+)([kKmMgG]?)', size_str)
    if not m:
        raise ArgumentError("'%s' is not a valid size string!" % (size_str))
    size = int(m.group(1))
    dimensions = {
        'k': 1024,
        'm': 1024*1024,
        'g': 1024*1024*1024,
    }
    dimension = m.group(2).lower()
    if dimension in dimensions:
        size = size * dimensions[dimension]
    return size


if __name__ == "__main__":

    from signal import signal, SIGQUIT
    from argparse import ArgumentParser, ArgumentError
    from time import time

    parser = ArgumentParser(description='Grep for regex in epub files')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Case-Insensitive matching')
    parser.add_argument('-n', '--min-matches', action='store', type=int, default=1, help='Minimum number of matches per file')
    parser.add_argument('--size-max', type=filesize, default='10M',
                        help='Maximum size for a file (compressed and uncompressed) to be considered. Supports size suffixes K,M,G. Default 10M')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show arguments before beginning to search')
    parser.add_argument('-V', '--version', action='version', version='epubgrep 0.2.1')

    parser.add_argument('pattern')
    parser.add_argument('file', nargs='+')
    args = parser.parse_args()

    if args.verbose:
        print("Pattern:", args.pattern)
        print("Maximum size:", args.size_max)
        print("Min matches:", args.min_matches)
        print("%signoring case" % ("not " if not args.ignore_case else ""))

    grep = EpubGrep(args.pattern)
    grep.setMinMatches(args.min_matches)
    grep.setIgnoreCase(args.ignore_case)
    grep.setMaxSize(args.size_max)

    started = time()

    def printstatus(signum, frame):
        time_spent = time()-started
        n = len(grep.already_visited)
        nps = n/time_spent
        print("Current Status: %d files visited (%f / s), currently at %s" % (n, nps, repr(grep.status)))
    signal(SIGQUIT, printstatus)

    for path in args.file:
        grep.searchin(path)
