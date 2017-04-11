# Builtin imports
import logging
import queue
import time
import threading
import json
# External imports
import falcon

log = logging.getLogger()

class RequireJSON:
    def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                'This API only supports responses encoded as JSON.')

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    'This API only supports requests encoded as JSON.')


class JSONTranslator(object):
    def process_request(self, req, resp):
        # req.stream corresponds to the WSGI wsgi.input environ variable,
        # and allows you to read bytes from the request body.
        #
        # See also: PEP 3333
        if req.content_length in (None, 0):
            # Nothing to do
            return

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')

        try:
            req.context['doc'] = json.loads(body.decode('utf-8'))

        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_500,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')

    def process_response(self, req, resp, resource):
        if 'result' not in req.context:
            return
        # Validate the JSON according the the API spec
        result_keys = req.context["result"].keys()
        key_check = lambda k: (k in result_keys and "id" in k.keys() and "type" in k.keys())
        if any([key_check(i) for i in  ["data", "errors", "meta"]]):
            resp.body = json.dumps(req.context['result'])
        else:
            log.error("Server response {0} to resource {1} failed to provide data key".format(
                req.context["result"], resource)
            )
            error_code = "500"
            resp.body = json.dumps({"errors": [{
                "type": "error",
                "id": "json_error",
                "status": error_code,

            }]})
            raise falcon.HTTPError("Invalid response", "The server has returned a malformed or invalid response. Please"
                                                       " submit a bug report to will@willbeddow.com.")


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
                            "for 15 minutes.\nOtherwise, if the ban is permanent, and you believe it's erroneous, "\
                            "you can contact me at will@willbeddow.com to possibly get the ban reversed."
            raise falcon.HTTPForbidden(title="Banned", description=error_message)


    def _ban_monitor(self):
        while self.running:
            # Look through the requests from the past 10 seconds
            ips = {}
            while not self._reqs.empty():
                ip = self._reqs.get()
                if ip in ips.keys():
                    ips[ip] += 1
                else:
                    ips.update({ip:1})
            for ip, num_requests in ips.items():
                ip_rate = num_requests/5
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
                            # Check to see if it's a permanently banned ip
                            if ip not in self._default_banned:
                                log.debug("Unbanning ip {0}".format(ip))
                                self.banned_ips.remove(ip)
                                del self._banned_silent[ip]
                    else:
                        self._banned_silent.update({ip:1})
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