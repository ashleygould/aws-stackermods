#!/usr/bin/env python

"""Help messages for stackermods blueprints

Usage:
    modhelp -m MODULE_NAME

Options:
    -m MODULE_NAME  Name of the blueprint module
"""

from docopt import docopt
import importlib



def main():
    args = docopt(__doc__)
    bp_module = importlib.import_module('stackermods.blueprints.' + args['-m'])
    bp_module.blueprint_help()

if __name__ == '__main__':
    main()
