# Copyright (c) 2013 Universidade Federal Fluminense (UFF), Polytechnic Institute of New York University.
# This file is part of noWorkflow. Please, consult the license terms in the LICENSE file.

import os
import persistence
from utils import print_msg

def execute(args):
    persistence.connect_existing(os.getcwd())
    print_msg('trials available in the provenance store:', True)
    for trial in persistence.load_all('trial'):
        script = os.path.basename(trial['script'])
        print '  Trial {id} of {} run at {start}'.format(script, **trial)

    
