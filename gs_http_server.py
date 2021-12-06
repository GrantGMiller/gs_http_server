import json
import re
from urllib.parse import unquote

import time

try:
    from extronlib_pro import event, EthernetServerInterfaceEx
except Exception as e:
    # use normal extronlib
    from extronlib import event
    from extronlib.interface import EthernetServerInterfaceEx


class HTTP_Server:
    def __init__(self, proc=None, port=5505, debug=False):
        self.proc = proc
        self.debug = debug
        self.defaultMethods = ["GET"]
        self.routes = []  # list of tuples [(pattern, methods, callback), ...]
        # Starts the Server Instance
        self.serv = EthernetServerInterfaceEx(port, "TCP")
        self.print("self.serv=", self.serv)
        res = self.serv.StartListen()
        if res != "Listening":
            print("self.serv.StartListen() res=", res)
            # this is not likely to recover
            raise ResourceWarning("Port unavailable")
        self._InitServerEvents()
        try:
            self.print(
                "{} server running at http://{}:{}".format(
                    type(self).__name__, self.IPAddress, self.IPPort
                )
            )
        except BaseException:
            pass

    @property
    def IPAddress(self):
        if self.proc is not None:
            return self.proc.IPAddress

    @property
    def IPPort(self):
        return self.serv.IPPort

    @staticmethod
    def BuildRoutePatterns(route):
        route_regex = re.sub(r"(<\w+>)", r"(?P\1[^\?]+)", route)
        return re.compile("^{}$".format(route_regex))

    def route(self, *args, **kwargs):
        def decorator(f):
            route_pattern = self.BuildRoutePatterns(args[0])
            if "methods" in kwargs:
                self.routes.append((route_pattern, kwargs["methods"], f))
            else:
                self.routes.append((route_pattern, self.defaultMethods, f))

            return f

        return decorator

    def GetRouteMatch(self, path):
        splits = path.split("?")
        path = splits[0]
        params = {}
        if len(splits) > 1:  # there are params like '?key=value&key2=value2
            for pair in splits[1].split("&"):
                k, v = pair.split("=")
                params[k] = v

        for route_pattern, methods, view_function in self.routes:
            m = route_pattern.match(path)
            if m:
                data = m.groupdict()
                if params:
                    data["params"] = params
                return data, methods, view_function

        return None

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def Serve(self, path, method=None, data=None):
        self.print(70, path, method, data)
        route_match = self.GetRouteMatch(path)
        self.print(71, route_match)
        if route_match:
            kwargs, methods, view_function = route_match
            # unquote any arguments
            for key, val in kwargs.items():
                try:
                    kwargs[key] = unquote(val)
                except BaseException:
                    pass

            self.print(73, kwargs, methods, view_function)
            if method in methods:
                if data is not None:
                    kwargs["data"] = data
                else:
                    kwargs["data"] = ""

                try:
                    kwargs["method"] = method
                    return self._FixViewFuncReturnType(view_function(**kwargs))
                except TypeError as e108:
                    self.print("Exception 108:", e108)
                    try:
                        kwargs.pop("data")
                        return self._FixViewFuncReturnType(
                            view_function(**kwargs))
                    except TypeError as e113:
                        self.print("Exception 113:", e113)
                        try:
                            kwargs.pop("method")
                            return self._FixViewFuncReturnType(
                                view_function(**kwargs))
                        except TypeError as e93:
                            self.print("Exception 93:", e93)
                            return "Error 91: {}".format(e93), 404
        else:
            return 'Error 93: Route "{}"" has not been registered'.format(
                path), 404
            # raise ValueError('Route "{}"" has not been registered'.format(path))

    def _FixViewFuncReturnType(self, ret):
        # the view function should return a tuple
        # if it returned a non-tuple, assume the user is implying a successfull
        # response ('ok', 200)
        if not isinstance(ret, tuple):
            return ret, 200
        else:
            return ret

    @staticmethod
    def NormalizeLineEndings(s):
        """Convert string containing various line endings like \n, \r or \r\n,
        to uniform \n."""

        return "".join((line + "\n") for line in s.splitlines())

    @staticmethod
    def StatusCode(status):
        codes = {
            200: "Ok\n",
            201: "Processed\n",
            401: "Unauthorized\n",
            404: "Unavailable\n",
        }
        return codes[status]

    # This receives and pushes the request to the appropriate method
    def DataProcess(self, client, data):

        # headers and body are divided with \n\n (or \r\n\r\n - that's why we
        # normalize endings). In real application usage, you should handle
        # all variations of line endings not to break request body
        request = self.NormalizeLineEndings(data)  # hack again
        requestSections = request.split("\n\n", 1)
        if len(requestSections) == 1:
            request_head, request_body = requestSections[0], ""
        else:
            request_head, request_body = requestSections

        # first line is request headline, and others are headers
        # Can process through headers if needed for future expansion
        # Such as looking for Content-Type
        request_head = request_head.splitlines()
        request_headline = request_head[0]
        # headers have their name up to first ': '. In real world uses, they
        # could duplicate, and dict drops duplicates by default, so
        # be aware of this.

        # request_headers = dict(x.split(': ', 1) for x in request_head[1:])

        # headline has form of "POST /can/i/haz/requests HTTP/1.0"
        request_method, request_uri, request_proto = request_headline.split(
            " ", 3)

        # print('Request Body', json.loads(request_body))

        # Checks if there's body data
        try:
            request_body = json.loads(request_body)
        except ValueError:
            pass

        try:
            response, code = self.Serve(
                request_uri, request_method, request_body)
        except TypeError as e:
            response, code = json.dumps({"Error": "Bad Request", 'Exception': str(e)}), 404
        self.DataReturn(client, {"Data": response, "StatusCode": code})
        # Temporary for testing return Trivial Data
        # self.DataReturn(client, data)

    # This is last in the sequence which  returns the HTTP request
    def DataReturn(self, client, data):

        response_body_raw = data["Data"]

        # Clearly state that connection will be closed after this response,
        # and specify length of response body
        response_headers = {
            "Content-Type": "application/json;encoding=utf8",
            "Content-Length": len(response_body_raw),
            "Connection": "close",
        }

        response_headers_raw = "".join(
            "{}: {}\n".format(k, v) for k, v in response_headers.items()
        )

        # Reply as HTTP/1.1 server, saying "HTTP OK" (code 200).
        response_proto = "HTTP/1.1"
        response_status = data["StatusCode"]
        response_status_text = self.StatusCode(data["StatusCode"])

        # sending all this stuff
        try:
            client.Send(
                "{} {} {}".format(
                    response_proto,
                    response_status,
                    response_status_text))

            client.Send(response_headers_raw)
            # to separate headers from body
            # (https://stackoverflow.com/questions/5757290/http-header-line-break-style#5757349)
            client.Send("\r\n")
            client.Send(response_body_raw.encode())

        except Exception as e2:
            self.print("Exception 188:", e2)

    def _InitServerEvents(self):
        @event(self.serv, "ReceiveData")
        def HandleReceiveData(client, data):
            self.print(
                "HandleReceiveData({}, {}".format(
                    client, data.decode()))
            self.DataProcess(client, data.decode())
            try:
                client.Disconnect()
                # This one time, I got this error for an unknown reason.
                # '''
                # Traceback (most recent call last):
                #   File "/connection_handler.py", line 914, in new_rx
                #     old_rx(client, data)
                #   File "/gs_http_server.py", line 190, in HandleReceiveData
                #     client.Disconnect()
                # ValueError: list.remove(x): x not in list
                # '''
            except Exception as e:
                print("{} Exception 207:".format(type(self).__name__), e)

        @event(self.serv, ["Connected", "Disconnected"])
        def HandleClientConnect(client, state):
            self.print("Client {} ({}).".format(state, client.IPAddress))


if __name__ == "__main__":
    app = HTTP_Server()

    @app.route("/test", methods=["GET", "POST"])
    def Test(*a, **k):
        print("Test(data=", a, k)
        return json.dumps(time.asctime()), 200

    print("end test")
