import os
def check(command):
    print "in check"
    exceptions = open("core/exceptions.txt").read().split('\n')
    e = False
    for item in exceptions:
        if "=" in item:
            trigger = item.split("=")[0]
            response = item.split("=")[1].split(":;:;:")
            if command in trigger or trigger in command:
                responsetype = response[0]
                if responsetype == "command":
                    e = "run:;:;:%s" % response[1]
                elif responsetype == "say":
                    e = "answer:;:;:%s" % response[1]
                elif responsetype=="urlbrowse":
                    import webbrowser
                    webbrowser.open(response[1])
                    e="completion:;:;:"
                elif responsetype=="urlsay":
                    e=urllib.urlopen(response[1])
                else:
                    e="error:;:;:unrecognized exception return type for exception triggered by: %s" %trigger
            else:
                pass
        else:
            pass
    if e != False:
        return e
    else:
        return e
