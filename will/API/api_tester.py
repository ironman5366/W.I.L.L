"""
Basic utility using easygui to submit API requests
Uses f-strings, so py >= 3.6 required
Will Beddow
"""
import easygui
import requests
import time

version = "1"

host = "http://127.0.0.1"

port = "8000"

api_path = f"{host}:{port}/api/v{version}/"
routing_template = api_path+"{}"

while True:
    route = easygui.enterbox("Please enter a route>")
    if not route:
        break
    final_route = routing_template.format(route)
    json_data = easygui.codebox(title="Request", msg="Request for {0}".format(final_route))
    start_time_str = time.strftime("%c")
    start_epoch_time = time.time()
    headers = {"content-type": "application/vnd.api+json"}
    r = requests.post(final_route, json=json_data, headers=headers)
    finish_epoch_time = time.time()
    time_delta = finish_epoch_time-start_epoch_time
    result = f"{r.status_code}\n{start_time_str}: {final_route}\nCompleted in {time_delta} seconds.\n\n{r.text}"
    easygui.codebox(text=result)