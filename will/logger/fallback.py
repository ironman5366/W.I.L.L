import sys
from termcolor import colored


def error(error_msg):
    sys.stderr.write(
        colored("CRITICAL: {0}\n".format(error_msg), 'red')
    )
