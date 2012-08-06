import os
import subprocess
import shutil

from sane_whitespace_hook import BAD_WS_REX

def all_match_group_names(rex, s):
    return set(k
               for match in rex.finditer(s)
               for k, v in match.groupdict().items()
               if v is not None)

def test_fixspace():
    os.chdir('test')
    shutil.copy('badspace.py', 'text-file')
    shutil.copy('no_final_newline', 'another-text-file')
    shutil.copy('some_binary', 'binary-file')
    shutil.copy('non_utf8', 'non-utf8-file')
    subprocess.check_call([os.path.join('..', 'fixspace'),
                           'text-file', 'another-text-file', 'binary-file',
                           'non-utf8-file'])
    badspace_fails = all_match_group_names(
        BAD_WS_REX, open('badspace.py', 'rb').read())
    assert badspace_fails == set(['cr', 'tab', 'trailing_lines', 'trailing_ws', 'utf8_bom'])
    no_final_newline_fails = all_match_group_names(
        BAD_WS_REX, open('no_final_newline').read())
    assert no_final_newline_fails == set(['no_final_newline', 'trailing_ws'])
    assert open('goodspace.py', 'rb').read() == open('text-file', 'rb').read()
    assert open('some_binary', 'rb').read() == open('binary-file', 'rb').read()
    assert open('non_utf8', 'rb').read() == open('non-utf8-file', 'rb').read()
    os.unlink('binary-file')
    os.unlink('text-file')
    os.unlink('another-text-file')
    os.unlink('non-utf8-file')

