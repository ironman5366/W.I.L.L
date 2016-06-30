import will
import easygui
import sys

will.run()

#Basic client debugging code
def command():
    command_str = easygui.enterbox(title="W.I.L.L",msg="Please enter a command.")
    if command_str:
        answer = will.main(command_str)
        easygui.msgbox(answer)
        command()
    else:
        if easygui.ynbox("Would you like to exit?"):
            sys.exit()
        else:
            command()
command()