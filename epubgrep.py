#!/usr/bin/env python3

import os
import re
import stat
import zipfile
import random
from textwrap import TextWrapper
from io import BytesIO


class EpubGrep(object):
    tag_pattern = re.compile(b'<[^>]+>')

    def __init__(self, pattern):
        self.already_visited = set([])
        if type(pattern) is str:
            pattern = pattern.encode('utf-8')
        self._pattern = pattern
        if type(pattern) is bytes:
            pattern = re.compile(pattern)
        self.pattern = pattern
        self.min_matches = 1
        self.ignore_case = False
        self.max_size = 10*1024*1024
        self.status = 'not started'
        self.preview = False
        self.preview_lead = 80
        self.preview_lag = 80
        self.randomize = False
        self.colorize = False
        self.output_width = 80

    def setColorize(self, color):
        self.colorize = color

    def setIgnoreCase(self, ignore):
        self.ignore_case = ignore
        if type(self._pattern) is bytes:
            self.pattern = re.compile(self._pattern, re.I if ignore else 0)

    def setMaxSize(self, size):
        self.max_size = size

    def setMinMatches(self, min):
        self.min_matches = min

    def setOutputWidth(self, width):
        self.output_width = width

    def setPreview(self, prev):
        self.preview = prev

    def setPreviewLead(self, lead):
        self.preview_lead = lead

    def setPreviewLag(self, lag):
        self.preview_lag = lag

    def setRandomize(self, rand):
        self.randomize = rand

    def read_pkzip(self, c):
        try:
            b = BytesIO(c)
            with zipfile.ZipFile(b, compression=zipfile.ZIP_DEFLATED, mode='r') as z:
                content = []
                for member in z.infolist():
                    if member.file_size > self.max_size:
                        continue
                    content.append(z.read(member.filename))
            return content
        except Exception as e:
            if self.colorize:
                print("Failed to open %s: %s" % (path, e))
            else:
                print("\033[1;31mFailed to open %s: %s\033[0;0m" % (path, e))
            return False

    def print_previews(self, matches):

        # Parts format: (start, end, string, isContext)
        def _match_to_parts(m):
            return [
                (max(m.start(0)-self.preview_lead, 0), m.start(0), m.string, True),
                (m.start(0), m.end(0), m.string, False),
                (m.end(0), m.end(0) + self.preview_lag, m.string, True)
            ]

        def _wrap(block):
            offs = 0
            lines = []
            while offs <= len(block):
                idx = block.find('\n', offs, offs+self.output_width-4)
                if idx == -1:
                    idx = offs+self.output_width-4
                lines.append('    '+block[offs:idx])
                offs = idx+1 if block[idx:idx+1] == '\n' else idx
            return '\n'.join(lines)

        def _print_block(block):
            block = EpubGrep.tag_pattern.sub(b'', block).strip()
            if len(block) == 0:
                return
            block = block.decode('utf-8', 'backslashreplace')
            print(_wrap(block), "\033[0;0m" if self.colorize else '')

        if len(matches) < 1:
            return

        matches.sort(key=lambda m: m.start(0))
        parts = _match_to_parts(matches[0])
        i = 2
        for m in matches[1:]:
            if parts[i][1] > m.start(0) and parts[i][2] is m.string:  # matches overlap, join together
                parts[i] = (parts[i][0], m.start(0), parts[i][2], parts[i][3])
                parts.append((m.start(0), m.end(0), m.string, False))
                parts.append((m.end(0), m.end(0) + self.preview_lag, m.string, True))
                i = i + 2
            else:
                parts = parts + _match_to_parts(m)
                i = i + 3

        block = b''
        last_was_context = False
        printed_something_already = False
        for p in parts:
            if not p[3]:  # this part is a match, not context
                last_was_context = False
                if self.colorize:
                    block = block + b'\033[1;31m%s' % (p[2][p[0]:p[1]])
                else:
                    block = block + p[2][p[0]:p[1]]
                continue
            if last_was_context:  # this is a new context block
                if printed_something_already:
                    print("---")
                _print_block(block)
                printed_something_already = True
                block = b''
            last_was_context = True
            if self.colorize:
                block = block + b'\033[1;36m%s' % (p[2][p[0]:p[1]])
            else:
                block = block + p[2][p[0]:p[1]]

        if printed_something_already:
            print("---")
        _print_block(block)

    def _searchcontent(self, path, content):
        n = 0
        matches = []
        for c in content:
            m = [match for match in self.pattern.finditer(c)]
            n = n + len(m)
            matches = matches + m
        if n >= self.min_matches:
            print("%s: %d" % (path.decode('utf-8', 'backslashreplace'), n))
            if self.preview:
                self.print_previews(matches)

    def _searchdir(self, path):
        try:
            realpath = os.path.realpath(path)
            if realpath in self.already_visited:
                return
            self.already_visited.add(realpath)
            self.status = path
            st = os.stat(realpath)
            mode = st.st_mode
            if stat.S_ISDIR(mode):
                ls = os.listdir(realpath)
                if self.randomize:
                    random.shuffle(ls)
                for sp in ls:
                    self._searchdir(os.path.join(path, sp))
            elif stat.S_ISREG(mode):
                if st.st_size > self.max_size:
                    return
                with open(realpath, mode='rb') as f:
                    c = f.read()
                if c.startswith(b'PK\x03\x04'):
                    content = self.read_pkzip(c)
                    if content:
                        self._searchcontent(path, content)
                        return
                self._searchcontent(path, [c])
                return
        except Exception as e:
            if self.colorize:
                print("\033[1;31mFailed to read %s: %s\033[0;0m" % (path.decode('utf-8', 'backslashreplace'), e))
            else:
                print("Failed to read %s: %s" % (path.decode('utf-8', 'backslashreplace'), e))

    def searchin(self, path):
        if type(path) is str:
            path = path.encode('utf-8')
        self._searchdir(path)
        self.status = 'finished'


def argument_filesize(size_str):
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


def argument_min_matches(min_str):
    min = int(min_str)
    if min <= 0:
        raise ArgumentError("min-matches must be greater than zero!")
    return min


def argument_ge_zero(n):
    n = int(n)
    if n < 0:
        raise ArgumentError("must be greater or equal to zero!")
    return n


if __name__ == "__main__":

    from signal import signal, SIGQUIT
    from argparse import ArgumentParser, ArgumentError
    from time import time
    from shutil import get_terminal_size

    parser = ArgumentParser(description='Search for a regular expression in EPUB files', epilog='Shows status information on SIGQUIT (Ctrl+\)')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='case-insensitive matching')
    parser.add_argument('--lag', action='store', type=argument_ge_zero, default=80, help='preview lag after matches for use with -p. Default 80')
    parser.add_argument('--lead', action='store', type=argument_ge_zero, default=80, help='preview lead before matches for use with -p. Default 80')
    parser.add_argument('-n', '--min-matches', action='store', type=argument_min_matches, default=1, help='minimum number of matches per file')
    parser.add_argument('--nocolor', action='store_false', dest='color', help='don\'t colorize output')
    parser.add_argument('-p', '--preview', action='store_true', help='preview matches')
    parser.add_argument('-r', '--randomize', action='store_true', help='randomize search order')
    parser.add_argument('--seed', action='store', type=int, default=random.randint(0, 2**32), help='seed for -r')
    parser.add_argument('--size-max', type=argument_filesize, default='10M',
                        help='maximum size for a file (compressed and uncompressed) to be considered. Supports size suffixes K,M,G. Default 10M')
    parser.add_argument('-v', '--verbose', action='store_true', help='show arguments before beginning to search')
    parser.add_argument('-V', '--version', action='version', version='epubgrep 0.2.2')

    parser.add_argument('PATTERN', help='python regular expression to search for')
    parser.add_argument('FILE', nargs='+', help='files or directories in which to search')
    args = parser.parse_args()

    if args.verbose:
        print("Searching in: ", args.FILE)
        print("Pattern:", args.PATTERN)
        print("Maximum size:", args.size_max)
        print("Min matches:", args.min_matches)
        print("%signoring case" % ("not " if not args.ignore_case else ""))
        if args.preview:
            print("Showing previews with %d lead and %d lag" % (args.lead, args.lag))
        if args.randomize:
            print("Randomizing directory traversal order, using seed %d" % (args.seed,))
        if args.color:
            print("Colorizing output")

    random.seed(args.seed)

    grep = EpubGrep(args.PATTERN)
    grep.setColorize(args.color)
    grep.setIgnoreCase(args.ignore_case)
    grep.setMaxSize(args.size_max)
    grep.setMinMatches(args.min_matches)
    grep.setPreview(args.preview)
    grep.setPreviewLag(args.lag)
    grep.setPreviewLead(args.lead)
    grep.setRandomize(args.randomize)
    grep.setOutputWidth(get_terminal_size(fallback=(80, 24)).columns)

    started = time()

    def printstatus(signum, frame):
        time_spent = time()-started
        n = len(grep.already_visited)
        nps = n/time_spent
        if args.color:
            print("\033[0;32mCurrent Status: %d files visited (%.2f / s), currently at %s\033[0;0m" % (n, nps, repr(grep.status)))
        else:
            print("Current Status: %d files visited (%.2f / s), currently at %s" % (n, nps, repr(grep.status)))
    signal(SIGQUIT, printstatus)

    try:
        for path in args.FILE:
            grep.searchin(path)
    except KeyboardInterrupt:
        printstatus(0, 0)
        if args.color:
            print("\033[0;32mInterrupted\033[0;0m")
        else:
            print("Interrupted")
