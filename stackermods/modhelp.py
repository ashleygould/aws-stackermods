#!/usr/bin/env python

"""Help messages for stackermods blueprints

Usage:
    stackermods <module>
    stackermods (-l | -h | -v)

where <module> is the name of a blueprint module

Options:
    -l, --list      Print listing of all blueprint modules in collection
    -h, --help      Print usage message
    -v, --version   Print version info
"""

import sys
import importlib
from docopt import docopt
import stackermods



def main():
    args = docopt(__doc__, version='stackermods %s' % stackermods.__version__)
    #print(args)
    if args['--list']:
        print('Available blueprint modules: %s' % ' '.join(stackermods.MODULES))
    elif args['<module>']:
        if args['<module>'] not in stackermods.MODULES:
            print('No such blueprint module: %s'% args['<module>'])
            sys.exit(1)
        print('Module: %s' % args['<module>'])
        print('Version: %s' % stackermods.__version__)
        bp_module = importlib.import_module('stackermods.blueprints.' + args['<module>'])
        bp_module.blueprint_help()

if __name__ == '__main__':
    main()
