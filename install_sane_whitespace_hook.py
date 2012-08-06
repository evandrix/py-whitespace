#!/usr/bin/env python
import ConfigParser
import os
import shutil
import sys

USAGE = '''\
install_sane_whitespace_hook HG_REPO_DIR ...

Installs a precommit hook to check for bad whitespace in HG_REPO_DIR.
'''
# FIXME: this still doesn't always display all violations although I'm not
#        sure why; probably because merges are handled specially?
#        In particular, merging 72bf686c21fb into e4a3bd4381cf
#        of bmc-server should show plenty of violations but didn't.


def update_hgrc(root_dir):
    dot_hg = os.path.join(root_dir, '.hg')
    hgrc = os.path.join(dot_hg, 'hgrc')
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                             'sane_whitespace_hook.py'),
                dot_hg)

    conf = ConfigParser.SafeConfigParser()
    conf.read(hgrc)
    if not conf.has_section('hooks'):
        conf.add_section('hooks')
    def add_precommit(name, *cmdparts):
        print "Adding a '%s' check" % name
        conf.set('hooks', 'pretxncommit.' + name, " ".join(cmdparts))
    print "Processing repo in %(root_dir)s" % vars()
    add_precommit('sane_whitespace',
                  'python:.hg/sane_whitespace_hook.py:master_hook')

    with open(hgrc, 'w') as fh:
        conf.write(fh)


# pylint: disable=C0103
if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] in ['--help', '-h', '-?']:
        print USAGE
    else:
        for hg_root in args:
            update_hgrc(hg_root)
