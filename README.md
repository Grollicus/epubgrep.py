epubgrep.py
=============

A simple search tool to search epub files

	usage: epubgrep.py [-h] [-i] [--lag LAG] [--lead LEAD] [-n MIN_MATCHES]
	                   [-m MAX_PREVIEWS] [--nocolor] [-p] [-r] [--seed SEED]
	                   [--size-max SIZE_MAX] [-v] [-V]
	                   PATTERN FILE [FILE ...]
	
	Search for a regular expression in EPUB files
	
	positional arguments:
	  PATTERN               python regular expression to search for
	  FILE                  files or directories in which to search
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -i, --ignore-case     case-insensitive matching
	  --lag LAG             preview lag after matches for use with -p. Default 80
	  --lead LEAD           preview lead before matches for use with -p. Default
	                        80
	  -n MIN_MATCHES, --min-matches MIN_MATCHES
	                        minimum number of matches per file
	  -m MAX_PREVIEWS, --max-previews MAX_PREVIEWS
	                        maximum number of previews to show per file
	  --nocolor             don't colorize output
	  -p, --preview         preview matches
	  -r, --randomize       randomize search order
	  --seed SEED           seed for -r
	  --size-max SIZE_MAX   maximum size for a file (compressed and uncompressed)
	                        to be considered. Supports size suffixes K,M,G.
	                        Default 10M
	  -v, --verbose         show arguments before beginning to search
	  -V, --version         show program's version number and exit
	
	Shows status information on SIGQUIT (Ctrl+\)

Examples
=============
Search for all epubs mentioning openssl (ignoring case)

	$ epubgrep.py -i openssl .

Search for all epubs mentioning openssl at least 3 times

	$ epubgrep.py -n 3 "[oO]pen[sS]{2}[lL]" .

Search for all epubs mentioning openssl at least 3 times and show up to 20 previews

	$ epubgrep.py -i -n 3 -p openssl .

