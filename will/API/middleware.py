# Builtin imports
import logging
import queue
import base64
import binascii
import threading
import json
import time

# External imports
import falcon

debug = False

log = logging.getLogger()


class RequireJSON:

    def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                'This API only supports responses encoded as JSON.')
        if req.method != "GET":
            if not req.content_type or 'application/json' not in req.content_type:
                resp.status = falcon.HTTP_UNSUPPORTED_MEDIA_TYPE
                req.context["result"] = {
                    "errors":
                        [{
                            "id": "UNSUPPORTED_MEDIA_TYPE",
                            "type": "error",
                            "status": resp.status,
                            "text": "This API only supports requests encoded as JSON"
                        }]
                }
                raise falcon.HTTPError(resp.status, "Unsupported media type")


class JSONTranslator:

    def process_request(self, req, resp):
        # req.stream corresponds to the WSGI wsgi.input environ variable,
        # and allows you to read bytes from the request body.
        #
        # See also: PEP 3333

        body = req.stream.read()
        if not body and req.method != "GET":
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "id": "REQUEST_EMPTY",
                        "type": "error",
                        "text": "Empty request body, a valid JSON document is required",
                        "status": resp.status
                    }]
            }
            raise falcon.HTTPError(resp.status, "Empty request")

        try:
            loaded_json = json.loads(body)
            doc_keys = loaded_json.keys()
            assert ("auth" in doc_keys and "data" in doc_keys)
            req.context["doc"] = loaded_json["data"]
            req.context["auth"] = loaded_json["auth"]
        except ValueError:
            resp.status = falcon.HTTP_500
            req.context["result"] = {
                "errors":
                    [{
                        "id": "JSON_MALFORMED",
                        "type": "error",
                        "status": resp.status,
                        "text": "Could not decode the request body. The "
                                "JSON was incorrect or not encoded as "
                                "UTF-8."
                    }]
            }
            raise falcon.HTTPError(falcon.HTTP_500, "Malformed JSON")
        # The data did not include both auth and data keys
        except AssertionError:
            resp.status = falcon.HTTP_BAD_REQUEST
            req.context["result"] = {
                "errors":
                    [{
                        "type": "error",
                        "id": "JSON_INCORRECT",
                        "status": resp.status,
                        "text": "The JSON data did not include top level `auth` and `data` keys."
                    }]
            }
            raise falcon.HTTPError(resp.status, "Incorrect JSON")

    @staticmethod
    def key_check(result):
        required_keys = ["text", "id", "type"]
        key_found = False
        for t, v in result.items():
            if t == "data":
                key_found = True
                if type(v) == dict:
                    for k in required_keys:
                        if k not in v.keys():
                            return False
                else:
                    return False
            elif t == "errors":
                key_found = True
                if type(v) == list:
                    for k in required_keys:
                            if k not in v[0].keys():
                                return False
                else:
                    return False
        return key_found

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return
        # Validate the JSON according the the API spec
        try:
            if self.key_check(req.context["result"]):
                resp.body = json.dumps(req.context['result'])
            else:
                log.error("Server response to resource {0} failed to provide data key".format(resource))
                error_code = falcon.HTTP_INTERNAL_SERVER_ERROR
                resp.status = error_code
                resp.body = json.dumps(
                    {"errors":
                        [{
                            "type": "error",
                            "id": "JSON_MALFORMED_ERROR",
                            "status": error_code,
                            "text": "The server has returned a malformed or invalid response. Please submit a bug "
                                    "report to will@willbeddow.com"
                        }]
                    }
                )
                raise falcon.HTTPError(resp.status, title="Error, invalid response")
        except Exception as e:
            log.error("Exception {0} occurred while decoding a JSON response to resource {1}".format(
                e.args, resource
            ))
            error_code = falcon.HTTP_INTERNAL_SERVER_ERROR
            resp.status = error_code
            resp.body = json.dumps(
                {"errors":
                    [{
                        "type": "error",
                        "id": "SERVER_JSON_DECODE_ERROR",
                        "status": error_code,
                        "text": "The server has returned a malformed or invalid response. Please submit a bug report "
                                "to will@willbeddow.com"
                    }]
                }
            )
            raise falcon.HTTPError(resp.status, title="Error, invalid response")


class AuthTranslator:
    """
    Decode authorization from various sources and puts everything into req.context["auth"]
    """

    @staticmethod
    def _b64_error(req, resp, header):
        resp.status = falcon.HTTP_BAD_REQUEST
        req.context["result"] = {
            "errors":
             [{
                "type": "error",
                "id": "HEADER_{}_INVALID".format(header.upper()),
                "text": "Passed {} header was not valid base64".format(header),
                "status": resp.status
            }]
        }
        raise falcon.HTTPError(resp.status, "Invalid encoding")

    def process_request(self, req, resp):
        """
        Decode headers or JSON post params into the required authentication headers and objects
        GET:
            - X-Client-Id
                - Required: True
                - Form: Plaintext
                - Post equivalent: auth/client_id
            - X-Client-Secret
                - Required: False
                - Form: Plaintext
                - Post equivalent: auth/client_secret
            - X-Access-Token
                - Required: False
                - Form: Plaintext
                - Post equivalent: auth/access_token
            - Authorization
                - Required: False
                - Form: Base64
                - Schema: username:password
                - Post equivalent: auth/username and auth/password
        POST:
            - auth
                - client_id
                    - required: True
            -  data
        :param req: The request object
        :param resp: The response object
        :return: 
        """
        if req.method == "GET":
            auth = {}
            client_id = req.get_header("X-Client-Id", required=True)
            auth.update({"client_id": client_id})
            client_secret = req.get_header("X-Client-Secret")
            if client_secret:
                auth.update({"client_secret": client_secret})
            access_token = req.get_header("X-Access-Token")
            if access_token:
                auth.update({"access_token": access_token})
            # Allow http basic auth
            authorization = req.get_header("Authorization")
            # Assume that it's a basic http authorization header with base64 encoded username:password
            if authorization:
                try:
                    decoded_header = base64.b64decode(authorization).decode('utf-8')
                    if ":" in decoded_header:
                        h_split = decoded_header.split(":")
                        username = h_split[0]
                        password = h_split[1]
                        auth.update({
                            "username": username,
                            "password": password
                        })
                    # Throw a bad request error
                    else:
                        resp.status = falcon.HTTP_BAD_REQUEST
                        req.context["result"] = {
                            "errors":
                                [{
                                    "type": "error",
                                    "id": "AUTHORIZATION_HEADER_INCOMPLETE",
                                    "text": "Didn't find colon separated username and password in decoded "
                                            "authorization header",
                                    "status": resp.status
                                }]
                        }
                        print (req.context)
                        raise falcon.HTTPError(resp.status, "Incomplete header")
                # Error decoding the authorization header from base64
                except binascii.Error:
                    self._b64_error(req, resp, "Authorization")
            req.context["auth"] = auth
        else:
            if "client_id" not in req.context["auth"].keys():
                resp.status = falcon.HTTP_BAD_REQUEST
                req.context["result"] = {
                    [{
                        "type": "error",
                        "id": "CLIENT_ID_NOT_FOUND",
                        "text": "Client id must be submitted in the authorization portion of every request",
                        "status": resp.status
                    }]
                }
                raise falcon.HTTPError(resp.status, "Client id not found")


class MonitoringMiddleware:
    """
    Middleware for checking ip rate limits
    """
    # Kill switch for the ban thread
    running = True
    _reqs = queue.Queue()
    _banned_silent = {}

    def process_request(self, req, resp):
        req_ip = req.access_route[0]
        self._reqs.put(req_ip)
        # Check if the ip is banned
        if req_ip in self.banned_ips:
            error_message = "Your ip has been either temporarily blacklisted for API misuse.\nIf you've been making " \
                            "an inordinate amount of API requests, you can make requests again after not making any " \
                            "for 15 minutes.\nOtherwise, if the ban is permanent, and you believe it's erroneous, " \
                            "you can contact me at will@willbeddow.com to possibly get the ban reversed."
            resp.status = falcon.HTTP_TOO_MANY_REQUESTS
            req.context["result"] = {
                "errors":
                    [{
                        "id": "IP_BANNED",
                        "type": "error",
                        "status": resp.status,
                        "text": error_message
                    }]
            }
            raise falcon.HTTPError(resp.status, title="Banned")

    def _ban_monitor(self):
        while self.running:
            # Look through the requests from the past 10 seconds
            ips = {}
            while not self._reqs.empty():
                ip = self._reqs.get()
                if ip in ips.keys():
                    ips[ip] += 1
                else:
                    ips.update({ip: 1})
            for ip, num_requests in ips.items():
                ip_rate = num_requests / 5
                if ip_rate >= 1.5:
                    self.banned_ips.append(ip)
                    log.debug("Banning ip {0}".format(ip))
            # If a temporarily offending ip is silent for 90 10 second intervals (15 minutes), unban it
            for ip in self.banned_ips:
                if ip not in ips.keys():
                    if ip in self._banned_silent:
                        self._banned_silent[ip] += 1
                        # The ip has been silent for more than 15 minutes and is suitable for unbanning
                        if self._banned_silent[ip] >= 180:
                            # Check to see if it's a permanently ("POST", "PUT", "DELETE")banned ip
                            if ip not in self._default_banned:
                                log.debug("Unbanning ip {0}".format(ip))
                                self.banned_ips.remove(ip)
                                del self._banned_silent[ip]
                    else:
                        self._banned_silent.update({ip: 1})
                else:
                    # If the ip is violating, delete it from banned_silent
                    if ip in self._banned_silent:
                        del self._banned_silent[ip]
            # Calculate it every 5 seconds
            time.sleep(5)

    def __init__(self, banned_ips=[]):
        # Set banned ips from args, should be set in config data
        self.banned_ips = banned_ips
        self._default_banned = banned_ips
        # Start a thread to ban suspicious ips
        ban_thread = threading.Thread(target=self._ban_monitor)
        ban_thread.start()
