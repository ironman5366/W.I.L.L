import will.plugins.API as API
import sys
import os
#TODO: finish this
@API.subscribe_to('open')
def open_sys(file):
    '''Open most files on the system using that systems builtin methods'''
    platform = sys.platform
    if not os.path.isfile(file):
        return 'File not found'
    if "win32" in platform:
        #If on windows
        open_command = "start .\{0}".format(file)
    elif "darwin" in platform:
        #If on os x
        open_command = "open {0}".format(file)
    elif "lin" in platform:
        #If on Linux
        open_command = "xdg-open {0}".format(file)