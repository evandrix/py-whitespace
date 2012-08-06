#!/usr/bin/env python
from __future__ import with_statement
import codecs
import re
import sys

USAGE = """Usage: fixspace [FILE]...
       fixspace --help

Normalize whitespace:
 - remove UTF-8 "BOM"
 - convert CR->LF
 - expand tabs (unix/python style)
 - delete trailing spaces and empty lines
 - ensure final newline

Files are modified in-place, binary files are ignored heuristically (if they
contain \0 or match a set of known binary extensions; this should generally do
the job, but be careful w/ short custom extension binary files). If no FILE is
given, read from STDIN and write to STDOUT.

BUGS

Currently just warns and skips files that aren't valid UTF8, so won't work
e.g. on latin1 files and other ASCII supersets although the regexp would work
for them as well. Should probably handle at least other unicode encodings.

Non-ASCII whitespace is not considered.
"""


BAD_WS_REX = re.compile('(?P<utf8_bom>\\A\xEF\xBB\xBF)|'
                        r'(?P<trailing_lines>(?<=\n)\s+\Z)|'
                        r'(?P<trailing_ws>[ \t]+\r*$)|'
                        r'(?P<cr>\r)|'
                        # need context to tabexpand; \S to avoid trailing
                        r'(?P<tab>^.*\t+ *\S)|'
                        r'(?P<no_final_newline>(?<=[^\n])\Z)',
                        re.M)

EXCEPTIONS = {r'(?:i)(?:^(?:gnu)?makefile)|'
              '[.](mk|(?:gnu)?makefile|make)$' : ['tab'],
              r'(?:i)[.](?:bat|inf)' : ['cr'],
              }

BINARY_EXTENSIONS = ['tsv', # not really binary, but we don't want to fuck up TSV files
                     'csv', # dito; CSV files often turn out to be TSV
                     'exe',
                     'com',
                     'obj',
                     'a',
                     'o',
                     'so',
                     'jar',
                     'class',
                     'pyd',
                     'dll',
                     'cab',
                     'msi',
                     'res',
                     'ogg',
                     'wav',
                     'mp3',
                     'mpg',
                     'mpeg',
                     'jpg',
                     'jpeg',
                     'png',
                     'gif',
                     'zip',
                     'tar',
                     'tgz',
                     'gz',
                     'bz2',
                     'iso',
                     ## crypto stuff where is_binary may fail due to short lengths
                     'gpg',
                     'key',
                     'spki',
                     'cert',
                     ]

def make_make_fixer(exceptions):
    def make_fixer(filename):
        noops = set(e
                    for (pat, exs) in exceptions
                    for e in exs if pat.search(filename or ''))

        def fixer(match):
            ((badness, match_data),) = (
                (what, it) for (what, it) in match.groupdict().items()
                if it is not None)
            if badness in noops:
                return match_data
            elif badness == 'tab':
                return match_data.expandtabs()
            elif badness == 'no_final_newline':
                return '\n'
            else:
                return ''
        return fixer
    return make_fixer

def binary_ext(filename):
    ext = filename.rpartition('.')[2].lower()
    return ext, ext in BINARY_EXTENSIONS

BOM_REGEXP = re.compile(r'\A' + '|'.join(
    [codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE,
     codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE]))

def is_binary(s):
    return '\0' in s and not BOM_REGEXP.match(s)

def aint_utf8(s):
    # TODO: try if utf-8 regexp solution is faster:
    # <http://www.w3.org/International/questions/qa-forms-utf-8.en.php>
    try:
        s.decode('utf8')
        return False
    except UnicodeDecodeError as e:
        return repr(e.object[e.start:e.end]), e.start

# XXX: list to learn additional binary extensions as you go;
#      not used yet
new_binary_exts = [] # pylint: disable=C0103
def fix_whitespace(filename, make_fixer):
    global new_binary_exts # pylint: disable=W0602
    if filename:
        ext, is_binary_ext = binary_ext(filename)
        if is_binary_ext:
            return
        with open(filename, 'rb+') as f:
            s = f.read()
            if is_binary(s):
                new_binary_exts.append(ext)
            else:
                bad_encoding = aint_utf8(s)
                if bad_encoding:
                    if BOM_REGEXP.match(s):
                        print >> sys.stderr, (
                            "%(filename)s is encoded as non-utf8 unicode"
                            ", skipping" % vars())
                        return
                    else:
                        bad_char, pos = bad_encoding
                        print >> sys.stderr, ("%(filename)s contains non-utf8 "
                                              "codepoint %(bad_char)s at %(pos)s, "
                                              "skipping"
                                              % vars())
                    return
                repl, n = BAD_WS_REX.subn(make_fixer(filename), s)
                if n and repl != s:
                    # XXX workaround for http://bugs.python.org/issue10328
                    repl = repl if repl.endswith('\n') else repl + '\n'
                    f.seek(0)
                    f.write(repl)
                    f.truncate()
    else:
        print BAD_WS_REX.sub(make_fixer(''), sys.stdin.read())

def main():
    args = sys.argv[1:]
    if args and args[0] in ('-h', '--help', '-?'):
        print USAGE
        sys.exit(0)
    if '--' in args: args.remove('--')

    make_fixer = make_make_fixer([(re.compile(k), v)
                                  for (k, v) in EXCEPTIONS.items()])
    if not args:
        fix_whitespace(None, make_fixer)
    else:
        for f in args:
            fix_whitespace(f, make_fixer)

if __name__ == '__main__':
    main()
