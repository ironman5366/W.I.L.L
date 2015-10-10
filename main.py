from flask import Flask
import threading
import os
import core.willexceptions as willexceptions
import core.plugins as plugins
import core.intent as intent
import datetime
import core.contentextract as contentextract
import personality.Personalityget as Personalityget
from flask import request

app = Flask(__name__)


@app.route("/")
def main():
    command = request.args.get("command", '')
    context = request.args.get("context", '')
    logfile=open("logs/mainlogs.txt", 'r+')
    logfile.write("started session at "+str(datetime.datetime.now())+"\n")
    logfile.write(command)
    logfile.write("command:"+str(command)+"\n")
    logfile.write(context+"\n")
    logfile.write("context:"+str(context)+"\n")
    logfile.write("before isexcept\n")
    isexcept = willexceptions.check(command)
    logfile.write("isexcept is:"+str(isexcept)+'\n')
    if isexcept != False:
        return isexcept
    if context == "greeting":
        logfile.write("context is greeting\n")
        greeting = Personalityget.get_greet(command)
        logfile.write("greeting is "+str(greeting)+"\n")
        return greeting
    elif context == "command":
        logfile.write("parsing operation\n")
        operation = intent.intentparse(command)
        contentextract.main(command)
        logfile.write("parsing command\n")
        logfile.write("operation came back %s" %str(operation)+"\n")
        if operation == False:
            return ("error:;:;:No operation detected")
        else:
            isopplugin = plugins.isplug(operation)
            if isopplugin == True:
                answer = plugins.run(operation, command)
                return answer
            else:
                logfile.write("going to intent2\n")
                intent2 = intent.check2(command, operation)
                if intent2 == False:
                    return ("error:;:;:Detected operation " + str(operation)) + " was not a valid command or plugin."
                else:
                    operation2 = intent2
                    isopplugin2 = plugins.isplug(operation2)
                    if isopplugin2 == False:
                        if operation==operation2:
                            o=True
                        else:
                            o=False
                        if o==False:
                            return ("error:;:;:Neither possible operations were valid commands or plugins. Possible operations were " + str( operation) + " and " + str(operation2) + ".")
                        else:
                            return (
                                "error:;:;:Possible operation was not a valid command or plugin. Possible operation was " + str(
                                operation))
                    else:
                        answer = plugins.run(operation, command)
                        return answer
    else:
        return ("error:;:;:unknown context " + str(context) + ". Acceptable contexts are greeting and command")


if __name__ == "__main__":
    print app.run(debug=True)
