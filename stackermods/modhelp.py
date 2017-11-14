#!/usr/bin/env python

"""Help messages for stackermods blueprints

Usage:
    modhelp -m MODULE_NAME

Options:
    -m MODULE_NAME  Name of the blueprint module
"""

from docopt import docopt
import importlib

if __name__ == '__main__':
    args = docopt(__doc__)
    module = importlib.import_module('blueprints.' + args['-m'])
    #module = importlib.import_module(args['-m'], 'stackermods.blueprints')
    module.help()


