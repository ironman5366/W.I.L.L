# Builtin imports
import sys
import time
import base64
# External imports
import requests

client_secret = sys.argv[1]

instance_url = "http://0.0.0.0:8000"

headers = {
    "Accept": "application/json"
}


def await_api(n):
    try:
        requests.get(instance_url)
    except requests.ConnectionError:
        if n>= 10:
            print ("API not up after 10 seconds, exiting")
            sys.exit(1)
        time.sleep(1)
        await_api(n+1)


def test_user_create():
    api_path = "/api/v1/users"
    req_auth = {
        "client_id": "web-official",
        "client_secret": client_secret
    }
    req_data = {
        "username": "holden",
        "password": "password",
        "first_name": "James",
        "last_name": "Holden",
        "settings":
            {
                "email": "will@willbeddow.com",
                "location":
                    {
                        "latitude": 44.970468,
                        "longitude": -93.262148
                    },
                "temp_unit": "C",
                "timezone": "US/Eastern"
            }
    }
    req = {
        "auth": req_auth,
        "data": req_data
    }
    req_path = instance_url+api_path
    resp = requests.post(req_path, json=req, headers=headers)
    json_data = resp.json()
    print(json_data)
    assert (json_data["data"]["id"] == "USER_CREATED")
    access_token = json_data["data"]["access_token"]
    return access_token


def test_start_session(access_token):
    api_path = "/api/v1/sessions"
    req_auth = {
        "client_id": "web-official",
        "client_secret": client_secret,
        "username": "holden",
        "password": "password",
        "access_token": access_token
    }
    req_path = instance_url+api_path
    req = {
        "auth": req_auth,
        "data": {}
    }
    resp = requests.post(req_path, json=req, headers=headers)
    print(resp.text)
    json_data = resp.json()
    session_id = json_data["data"]["session_id"]
    return session_id


def test_user_exists(session_id):
    api_path = "/api/v1/users/holden"
    # Generate an auth header
    req_headers = {
        "X-Client-Id": "web-official",
        "X-Session-Id": session_id
    }
    req_headers.update(headers)
    print("Submitting with headers {}".format(req_headers))
    req_path = instance_url+api_path
    resp = requests.get(req_path, headers=req_headers)
    print(resp.text)

if __name__ == "__main__":
    # Wait for the API to be up
    await_api(1)
    access_token = test_user_create()
    session_id = test_start_session(access_token)
    test_user_exists(session_id)