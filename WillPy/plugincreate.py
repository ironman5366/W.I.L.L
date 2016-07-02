import json
import os
import sys
import easygui
import tkFileDialog
import shutil
from Tkinter import Tk

# Make it so that the window doesn't stay open
root = Tk()
root.withdraw()


def main():
    '''Create a plugin getting data using easygui'''

    def getdata(inputtype, easyguiargs):
        '''Use easygui methods to get data and check if the user wants to exit if they hit cancel'''
        print inputtype
        print easyguiargs
        if inputtype != "enterbox" and inputtype != "msgbox" and inputtype != "ynbox":
            print easyguiargs
            print easyguiargs[0]
            print easyguiargs[1]
            answer = getattr(easygui, inputtype)(easyguiargs[0], "Create a plugin", easyguiargs[1])
        else:
            answer = getattr(easygui, inputtype)(easyguiargs)
        if answer != None:
            return answer
        else:
            if easygui.ynbox("Would you like to exit?"):
                sys.exit()
            else:
                getdata(inputtype, easyguiargs)

    plugname = getdata("enterbox", "What would you like to name the plugin?")
    # Add more choices here if the plugin module gets increased variability
    typechoices = ["Python", "Terminal Command"]
    plugtype = getdata("buttonbox", ("Please pick a plugintype", typechoices))
    if plugtype == typechoices[0]:
        formalplugtype = 'python'
    elif plugtype == typechoices[1]:
        formalplugtype = 'exec'
    else:
        easygui.msgbox("Unrecognized plugin type {0}".format(plugtype))
        sys.exit()
    required = []
    possiblerequired = ["command", "name", "email", "phone", "time", "date"]
    for item in possiblerequired:
        if getdata('ynbox', 'Does your plugin require {0} to be passed to it?'.format(item)):
            required.append(item)
        else:
            pass
    syns = []
    synsraw = getdata("enterbox",
                      "Please enter all synonym words or phrases for your plugin, seperated with commas. No spaces in between synonyms. If there are no synonyms, just hit OK.")
    if ',' in synsraw:
        for item in synsraw.split(','):
            syns.append(item)
    else:
        if synsraw != '':
            syns.append(str(synsraw))
        else:
            pass
    if getdata('ynbox',
               "Would you like to pass the first word of the command to the plugin (If you don't understand what this means hit yes)"):
        firstword = "yes"
    else:
        firstword = "no"
    qtchoices = ["Any", "None", "Some"]
    qts = getdata("buttonbox", (
    "Which question words (if any) should activate your plugin? (Some means only those which can only be interpreted as a question word)",
    qtchoices))
    if qts == qtchoices[0] or qts == qtchoices[2]:
        q = True
        priority = open('priority.txt').read().split('\n')
        prioritized = []
        for line in priority:
            name = line.split(':')[1]
            status = line.split(':')[0]
            prioritized.append({status: plugname})
        priorlistprint = ''
        for item in prioritized:
            priorlistprint += ('{0}: {1}\n'.format(item[0], item[1]))

        def getpriornum():
            priority = getdata('enterbox',
                               "Please pick the priority of which your question plugin WillPy be activated by entering a number. These are the current numbers, the larger ones are higher priorities. (Search should probably stay last) {0}".format(
                                   priorlistprint))
            try:
                prionum = int(priority)
            except TypeError:
                easygui.msgbox("Must be a number")
                getpriornum()

        if getdata('ynbox',
                   "Would you like to make changes to the priority file? (After this is done it has to be manually undone)"):
            f = open('priority.txt').read()
            for line in f:
                try:
                    num = int(line.split(':')[0])
                    if num <= priornum:
                        f = f.replace(line, line.replace(str(num), str(num - 1)))
                except TypeError:
                    pass
            f += "{0}:{1}\n".format(str(priornum), str(plugname))
            newprior = open('priority.txt', 'w')
            newprior.write(f)
            newprior.close()
        else:
            sys.exit()
    else:
        q = False
    rtypes = ["Answer", "Completion"]
    returntype = getdata('buttonbox', (
    "Does your plugin return an answer or should WillPy just report completion of the task?", rtypes))
    os.chdir('plugins')
    os.makedirs(plugname)
    jsoninfo = [{"name": plugname}, {"type": formalplugtype}, {"firstword": firstword}, {'synonyms': syns},
                {"require": required}, {'questiontriggers': qts.lower()}, {'returns': returntype.lower()}]
    # If the user selects a python plugin
    if plugtype == typechoices[0]:
        pyfile = tkFileDialog.askopenfilename()
        print pyfile
        pyfilename = str(pyfile)
        print pyfilename
        pyfunction = getdata('enterbox', 'What function should WillPy call?')
        pyfilecopyname=pyfilename.split("/")[-1]
        print pyfilecopyname
        print pyfile
        copypath='{0}/{1}'.format(plugname, pyfilecopyname)
        print copypath
        shutil.copyfile(pyfile,copypath)
        jsoninfo.append({"file": pyfilecopyname})
        jsoninfo.append({"function": pyfunction})
    # If the user selects a terminal command plugin
    elif plugtype == typechoices[1]:
        commandstructure = getdata("enterbox",
                                   "Please enter the structure of your terminal command that WillPy be executed. If you stated that one of the arguments of command, name, email, phone, time, or date, please type the word inside the terminal command.")
        jsoninfo.append({"structure": commandstructure})
    else:
        print "Unrecognized plugin type {0}".format(str(plugtype))
        sys.exit()
    finaljson = json.dumps(jsoninfo)
    os.chdir(plugname)
    f = open('plugin.json', 'w')
    f.write(finaljson)
    f.close()
    easygui.msgbox("Done")
    sys.exit()


if __name__ == "__main__":
    main()
