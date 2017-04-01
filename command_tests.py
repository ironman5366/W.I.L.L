import unittest
import os
import json
import requests
#Unit tests that directly request commands

if os.path.isfile("debug_will.conf"):
    data_string = open("debug_will.conf").read()
    json_data = json.loads(data_string)
    configuration_data = json_data
    #A debugging account
    username = configuration_data["username"]
    password = configuration_data["password"]
    local_url = "http://{0}:{1}".format(
        configuration_data["host"],
        configuration_data["port"]
    )
else:
    print ("Couldn't find will.conf file, exiting")
    os._exit(1)

session_id = None

class test_2_commands(unittest.TestCase):
    def send_command(self, command):
        r = requests.post(
            url="{0}/api/command".format(local_url), data={"session_id": session_id, "command": command}).json()
        self.assertTrue(r["type"] == "success")
        return r
    def test_commands(self):
        commands = {
            "How are you?": lambda x: "well, thank you" in x,
            "What's the weather like?": lambda x: "Weather for" in x,
            "Read me the news": lambda x: bool(x.strip())
        }
        for command in commands:
            result = self.send_command(command)
            print(result)
            self.assertTrue(commands[command](result['text']))

class test_1_session_handling(unittest.TestCase):
    def start_session(self):
        global session_id
        #TODO: use the host and port to communicate with the debug server
        r = requests.post(url="{0}/api/start_session".format(local_url), data={
            "username": username, "password": password}
                          ).json()
        print (r)
        self.assertTrue("session_id" in r["data"].keys())
        session_id = r["data"]["session_id"]
    def check_session(self):
        r = requests.post(url="{0}/api/check_session".format(local_url), data={"session_id": session_id}).json()
        print (r)
        self.assertTrue("valid" in r["data"].keys())
        self.assertTrue(r["data"]["valid"])
    def test_sessions(self):
        self.start_session()
        self.check_session()




if __name__ == '__main__':
    unittest.main()
