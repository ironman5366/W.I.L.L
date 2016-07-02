import WillPy
import easygui
import sys
import json

WillPy.run()

def command():
    command_str = easygui.enterbox(title="WillPy", msg="Please enter a command.")
    def command_process(command_str):
        if command_str:
            answer = WillPy.main(command_str)
            answer_json = json.loads(answer)
            answer_text = answer_json["text"]
            answer_type = answer_json["return_type"]
            answer_action = answer_json["return_action"]
            if answer_type == "answer":
                easygui.msgbox(title="WillPy", msg=answer_text)
            else:
                def enter_response():
                    response_text = easygui.enterbox(title="WillPy", msg=answer_text)
                    if response_text:
                        response = {}
                        response.update({"response_args":response_text,"response_type":answer_type, "return_action":answer_action})
                        for key in answer_json.keys():
                            if not response[key]:
                                response.update({key:answer_json[key]})
                        new_answer = WillPy.main(response)
                        command_process(new_answer)
                    else:
                        if easygui.ynbox(title="WillPy", msg="Would you like to exit?"):
                            sys.exit()
                        else:
                            enter_response()
                enter_response()
        else:
            if easygui.ynbox(title="WillPy",msg="Would you like to exit?"):
                sys.exit()
            else:
                command()
    command_process(command_str)
command()
