#!/usr/bin/env python
# FIXME(alexander): got more complicated so should get its own unittest
from __future__ import with_statement
import codecs
import itertools
import re

from mercurial import util
from mercurial.node import short

BOM_REGEXP = re.compile(r'\A' + '|'.join(
    [codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE,
     codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE]))

def is_binary(s):
    return '\0' in s and not BOM_REGEXP.match(s)


def line_and_column_at(s, pos):
    if pos > len(s): # not >= because of \Z matches
        raise IndexError("`pos` %d not in string" % pos)
    # *don't* count last '\n', if it is at pos!
    line = s.count('\n', 0, pos)
    if line:
        return line + 1, pos - s.rfind('\n', 0, pos) - 1
    else:
        return 1, pos


def master_hook(ui, repo, node, **kwargs):
    ui.debug('kwargs: %s\n' % kwargs)
    # The mercurial hook script expects the equivalent of an exit code back from
    # this call:
    #   False = 0 = No Error : allow push
    #   True = 1 = Error : abort push
    failed = any(fail(ui, repo, node, **kwargs) for fail in FAILS)
    if failed:
        # Save the commit message so it can be reused by user
        desc = repo[repo[node].rev()].description()
        ui.debug('Commit Message: %s\n' % desc)
        with open('%s/.hg/commit.save' % repo.root, 'w')  as f:
            f.write(desc)
        ui.warn('Commit message saved to .hg/commit.save\n'
                'After fixing, retry with ``hg commit -l .hg/commit.save``\n')
    return failed

BAD_WS_REX = re.compile('(?P<utf8_bom>\\A\xEF\xBB\xBF)|'
                        r'(?P<trailing_lines>(?<=\n)\s+\Z)|'
                        r'(?P<trailing_ws>[ \t]+\r*$)|'
                        r'(?P<cr>\r)|'
                        r'(?P<tab>\t+)|'
                        r'(?P<no_final_newline>(?<=[^\n])\Z)',
                        re.M)

def show_badness(ui, f, data, start, baddy, rev=None,
                 badness='bad whitespace'):
    assert f # make pylint happy
    lineno, col = line_and_column_at(data, start)
    # pylint: disable=W0612
    line = data.split('\n')[lineno-1]
    marker = ' ' * col + '^' * min(len(baddy), 1)
    baddy_info = repr(baddy) if baddy else 'No final newline'
    ui.warn((('%(f)s:%(lineno)d:%(col)d: [rev %(rev)s] '
              'contains %(badness)s (%(baddy)r)\n' if rev else '') +
             '%(f)s:%(lineno)d:%(col)d: %(line)s\n'
             '%(f)s:%(lineno)d:%(col)d: %(marker)s (%(baddy_info)s)\n') %
            vars())


def decode(ui, f, rev, raw_data, failed):
    """Turn `raw_data` into unicode, prompting on encoding problems.

    If ``failed='&Show'`` is passed in no prompting happens.

    Returns (failed, data) -- failed is a generalized boolean (either False,
    True or '&Show' which means continue showing problems).
    """
    assert not failed or failed == '&Show'
    try:
        # N.B: we actually throw away the result if it's utf8
        # as BAD_WS_REX  will operate correctly on strs w/ utf8 payload
        raw_data.decode('utf8')
        data = raw_data
    except UnicodeDecodeError, e:
        # check if it's another unicode encoding (w/ BOM)
        # TODO: also try platform default encoding?
        for bits, bo in itertools.product([16, 32], ['LE', 'BE']):
            if raw_data.startswith(getattr(codecs, 'BOM_UTF%s_%s' % (
                bits, bo))):
                data = raw_data.decode('utf%s' % bits)
                ui.warn('%(f)s is utf%(bits)s-%(bo)s (not utf8)\n' % vars())
                break
        else:
            data = raw_data
            show_badness(ui, f, data, e.start, e.object[e.start:e.end],
                         rev=rev if not failed else None,
                         badness='a non-utf codepoint '
                         '(unknown encoding)')
        if not failed:
            utf_ans_choice = ('&No', '&Yes', '&Show')
            utf_ans = utf_ans_choice[ui.promptchoice(
                'Ignore the encoding for this file and continue:'
                '[y]es, [N]o, abort but [s]how all violations?',
                utf_ans_choice, 0)]
            failed = utf_ans != '&Yes' and utf_ans
    return failed, data

def whitespace_check_fails(ui, f, rev, data, failed):
    """Check basestring `data`, prompt on whitespace problems.

    If ``failed='&Show'`` is passed in no prompting happens.

    Returns failed which is a generalized boolean (either False,
    True or '&Show' which means continue showing problems).
    """
    assert not failed or failed == '&Show'
    for match in BAD_WS_REX.finditer(data):
        ui.debug('Match in %(f)s, failed=%(failed)s\n' % vars())
        if not failed:
            show_badness(ui, f, data, match.start(), match.group(), rev=rev)
            # pylint: enable=W0612
            ans_choice = ('&No', '&Yes', '&Ignore', '&Show')
            ans = ans_choice[ui.promptchoice(
                'Allow this violation and continue: '
                '[y]es, [N]o, [i]gnore file, '
                'abort but [s]how all violations?',
                ans_choice, 0)]
            ui.debug('ans is %s\n' % ans)
            if ans == '&Ignore':
                break
            failed = failed or match and ans != '&Yes' and ans
        elif failed == '&Show':
            show_badness(ui, f, data, match.start(), match.group())
    return failed


def bad_whitespace_hook(ui, repo, node, **kwargs): # pylint: disable=R0914,W0613
    seen = set()
    tip = repo['tip']
    failed = False
    for rev in xrange(len(repo)-1, repo[node].rev()-1, -1):
        c = repo[rev]
        for f in c.files():
            if f in seen or f not in tip or f not in c:
                continue
            ui.debug('inspecting %(f)s\n' % vars())
            seen.add(f)
            raw_data = c[f].data()
            if not is_binary(raw_data):
                bad_encoding, data = decode(ui, f, short(c.node()),
                                            raw_data, failed)
                failed = failed or bad_encoding
                if not failed or failed == '&Show':
                    failed = whitespace_check_fails(ui, f, rev, data, failed)
                else:
                    break

    return bool(failed)

FAILS = [bad_whitespace_hook]
