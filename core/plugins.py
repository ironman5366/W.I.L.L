import os
import subprocess
import argfetcher
def isplug(keyword):
    rootdir="plugins"
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            if file==keyword+".will":
                return True
            else:
                pass
    return False
def run(plugin, operation):
    print plugin
    executable=open("plugins/"+plugin+".will").read()
    flines = executable.split('\n')
    if "type=" in flines[0]:
        typevar=flines[0].split("type=")[1]
        if typevar=="python":
            if "file=" in flines[1]:
                pyfile=flines[1].split("file=")[1]
                print pyfile
                pyimport=pyfile+".py"
                print pyimport
                import imp
                try:
                    imvar = imp.load_source('plugfile', pyimport)
                    if "function=" in flines[2]:
                        plugfunction=flines[2].split("function=")[1]
                        flines.remove("type=python")
                        flines.remove("file="+pyfile)
                        flines.remove("function="+plugfunction)
                        required=[]
                        for item in flines:
                            if "required=" in item:
                                requiredobject = item.split("required=")[1]
                                required.append(requiredobject)
                                print requiredobject
                        argfetcher.main(operation, required)
                        fetched=open("core/content/args.txt").read().split("\n")
                        print fetched
                        needed=[]
                        for item in fetched:
                            for i in required:
                                if i in item and "None" in item:
                                    needed.append(i)
                        if not needed:
                            print "in not needed bool conditional"
                            finalargs=[]
                            print "required:"+str(required)
                            print "fetched:"+str(fetched)
                            for item in required:
                                for i in fetched:
                                    if i.split("=")[0] == str(item):
                                        print "Item is in fetched, item is "+str(item)+" and fetched is "+str(i)
                                        finalargs.append(i.split("=")[1])
                            try:
                                result = getattr(imvar, plugfunction)(finalargs)
                                return str(result)
                            except ValueError:
                                return "error:;:;:could not run function specified by plugin"
                        else:
                            needfile=open("core/content/needed.txt", 'w')
                            for item in needed:
                                needfile.write(item+'\n')
                            return "needed-mult:;:;"
                except ImportError:
                    return "error:;:;:could not import specified python module"
            else:
                return"error:;:;:Plugin type is python file but no file location provided"
        elif typevar=="url":
            import urllib
            if "base=" in flines[1]:
                base=flines[1].split("base=")[1]
                if "postaction=" in flines[2]:
                    postaction = flines[2].split("postaction=")[1]
                    if postaction != "display-raw" and postaction != "display-text" and postaction!= "write-raw" and postaction != "write-text":
                        return "error:;:;:url plugin did not specify a valid method of dealing with returned data"
                    flines.remove("type=url")
                    flines.remove("base="+base)
                    flines.remove("postaction="+postaction)
                    for item in flines:
                        if "param:" in item:
                            if "willvar=" in item:
                                if "paramname" in item:
                                    paramname=item.split("param:")[1].split("-")[0]
                                else:
                                    return "error:;:;:the plugin file specified no name for the parameter"
                                willvar=item.split("param:"+paramname+"-willvar=")[1]
                                if willvar != "command":
                                    return "error:;:;:the only url variable currently supported is command"
                                else:
                                    willvar=operation
                                    f = {paramname : willvar}
                                    f=urllib.urlencode(f)
                                    finalurl=base+f
                                    try:
                                        import xml
                                        html = urllib.urlopen(f)
                                        if postaction=="display-raw":
                                            return "answer:;:;:"+str(html)
                                        elif postaction=="display-text":

                                            return "answer:;:;:"+str(''.join(xml.etree.ElementTree.fromstring(html).itertext()))
                                        elif postaction=="write-raw":
                                            for item in flines:
                                                if "writename=" in item:
                                                    writename=item.split("writename=")[1]
                                            wfiler = open(writename, 'w')
                                            wfiler.write(html)
                                            wfiler.close
                                        elif postaction=="write-text":
                                            for item in flines:
                                                if "writename=" in item:
                                                    writename=item.split("writename=")[1]
                                            wfiles = open(writename, 'w')
                                            html = str(''.join(xml.etree.ElementTree.fromstring(html).itertext()))
                                            wfiles.write(html)
                                            wfiles.close
                                            return "completion:;:;:"
                                    except:
                                        return "error:;:;There was an error opening the url provided by the plugin file. Please check the syntax of the url and make sure the parameters are supported"

                else:
                    return "error:;:;:url plugin did not specify how to display returned information"
            else:
                return "error:;:;:url based plugin did not specify base url"
        elif typevar=="executable":
            import os
            import sys
            executable = flines[1].split("file=")[1]
            if sys.platform == 'linux2':
                subprocess.call(["xdg-open", executable])
            else:
                os.startfile(executable)
    else:
        if "link=" in flines[0]:
            plugin=flines[0].split("link=")[1]
            run(plugin,operation)
        else:
            return "error:;:;:plugin file did not provide required information"
