import WillPy.plugins.API as API
import sys
import os
#TODO: finish this
@API.subscribe_to({
"name": "open",
"ents_needed" : False,
"structure" : {"needed":["VERB"]},
"questions_needed" : False,
"key_words" : ["open"]})
def open_sys(*args, **kwargs):
    '''Open most files on the system using that systems builtin methods'''
    print "In open_sys"
    file = args[1]
    platform = str(sys.platform)
    print platform
    if not os.path.isfile(file):
        return 'File {0} not found'.format(file)
    if "win32" in platform:
        #If on windows
        open_command = "start {0}".format(file)
    elif "darwin" in platform:
        #If on os x
        open_command = "open {0}".format(file)
    elif "lin" in platform:
        #If on Linux
        open_command = "xdg-open {0}".format(file)
    os.system(open_command)
    return "Done"