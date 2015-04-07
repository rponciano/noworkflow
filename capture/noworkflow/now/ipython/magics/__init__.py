# Copyright (c) 2015 Universidade Federal Fluminense (UFF)
# Copyright (c) 2015 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.

from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from IPython.core.magic import Magics, magics_class

from .now_run import NowRun
from .now_ipython import NowIpython
from .now_set_default import NowSetDefault
from .now_sql import NowSQL
from .now_prolog import NowProlog


MAGICS = [
	('now_run', 'line_cell', NowRun),
	('now_ip', 'line', NowIpython),
	('now_set_default', 'line', NowSetDefault),
    ('now_sql', 'cell', NowSQL),
	('now_prolog', 'cell', NowProlog),
]


@magics_class
class NoworkflowMagics(Magics):

    def __init__(self, shell):
        super(NoworkflowMagics, self).__init__(shell=shell)
        self.commands = [
        	cls(command, cls.__doc__, magic_type=magic_type)
        	for command, magic_type, cls in MAGICS
        ]
        self._generate_magics()

    def _generate_magics(self):
        for command in self.commands:
            command.add_arguments()
            def func(line, cell=None, c=command):
                return c.execute(c.func, line, cell, self)

            command.func = command.create_magic(func)
            for typ in command.magic_type.split('_'):
                self.magics[typ][command.magic] = command.func


def register_magics(ipython):
    if not ipython:
        ipython = get_ipython()
    magics = NoworkflowMagics(ipython)
    ipython.register_magics(magics)