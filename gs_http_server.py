import re
import json
from collections import defaultdict

import time
from extronlib import event
from urllib.parse import unquote
from extronlib.system import File
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
                kwargs['methods'] = [m.upper() for m in kwargs['methods']]  # ensure upper case
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
                data = defaultdict(lambda: None)
                data.update(m.groupdict())
                if params:
                    data["params"] = params
                return data, methods, view_function

        return None

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def Serve(self, request):
        self.print('87 req=', request)
        route_match = self.GetRouteMatch(request.path)
        self.print(71, route_match)
        if route_match:
            kwargs, methods, view_function = route_match
            # unquote any arguments
            for key, val in kwargs.items():
                if val:
                    try:
                        kwargs[key] = unquote(val)
                    except BaseException:
                        pass

            self.print(73, kwargs, methods, view_function)
            if request.method in methods:
                try:
                    return self._FixViewFuncReturnType(
                        view_function(request, **kwargs),
                    )
                except TypeError as e108:
                    self.print("Exception 108:", e108)
                    try:
                        return self._FixViewFuncReturnType(
                            view_function(request),
                        )
                    except TypeError as e113:
                        self.print("Exception 113:", e113)
                        try:
                            return self._FixViewFuncReturnType(
                                view_function(),
                            )
                        except TypeError as e93:
                            self.print("Exception 93:", e93)
                            return "Error 91: {}".format(e93), 404
        else:
            return 'Error 93: Route "{}"" has not been registered'.format(
                request.path), 404
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
    def StatusCode(status):
        codes = {
            200: "Ok\n",
            201: "Processed\n",
            401: "Unauthorized\n",
            404: "Unavailable\n",
        }
        return codes[status]

    # This receives the raw HTTP request
    def DataProcess(self, client, data):
        self.print('156', client, data)
        request = Request(raw=data)
        self.print('157 req=', request)
        try:
            response, status_code = self.Serve(request)
        except TypeError as e:
            response, status_code = json.dumps({"Error": "Internal Server Error", 'Exception': str(e)}), 500

        self.DataReturn(client, response, status_code)

    def DataReturn(self, client, response, status_code):
        # This is last in the sequence. It actually sends the raw response back to the client.

        if isinstance(response, str):
            response_body_raw = response

            # Clearly state that connection will be closed after this response,
            # and specify length of response body
            response_headers = {
                "Content-Type": "application/json;encoding=utf8",
                "Content-Length": len(response_body_raw),
                "Connection": "close",
            }

        elif isinstance(response, Response):
            response_headers = response.headers.copy()
            response_headers.update({
                "Content-Length": len(response.body),
                "Connection": "close",
            })
            response_body_raw = response.body

        response_headers_raw = "".join(
            "{}: {}\n".format(k, v) for k, v in response_headers.items()
        )

        # Reply as HTTP/1.1 server, saying "HTTP OK" (code 200).
        response_proto = "HTTP/1.1"
        response_status = status_code
        response_status_text = self.StatusCode(status_code)

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


def NormalizeLineEndings(s):
    """Convert string containing various line endings like \n, \r or \r\n,
    to uniform \n."""
    return '\n'.join(s.splitlines())


import collections


class CaseInsensitiveDict(dict):

    def __getitem__(self, k):
        k = k.lower()
        if k not in self:
            return None
        return super().__getitem__(k)

    def __setitem__(self, k, v):
        k = k.lower()
        return super().__setitem__(k, v)

    def get(self, k, *args, **kwargs):
        return super().get(k.lower(), *args, **kwargs)


class Request:
    # should follow https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
    def __init__(self, raw, **kwargs):
        self.raw = NormalizeLineEndings(raw)
        self.kwargs = kwargs

        # parse
        requestSections = self.raw.split("\n\n", 1)
        if len(requestSections) == 1:
            self.rawHeaders, self.data = requestSections[0], ''
        else:
            self.rawHeaders, self.data = requestSections

        self.content_length = len(self.data)

        headerSplit = self.rawHeaders.splitlines()

        self.method, self.path, self.protocol = headerSplit[0].split(' ', 3)
        self.method = self.method.upper()

        self.args = CaseInsensitiveDict()
        if '?' in self.path:
            s = self.path.split('?', 2)[-1]
            for pair in s.split('&'):
                k, v = pair.split('=', 2)
                self.args[k] = v

        try:
            self.json = json.loads(self.data)
            self.is_json = True
        except:
            self.json = None
            self.is_json = False

        self.raw_request_line = headerSplit[0]

        self.headers = CaseInsensitiveDict()
        for line in headerSplit[1:]:
            key, value = line.split(': ', 2)
            if key not in self.headers:
                self.headers[key] = value
            else:  # duplicate keys
                self.headers[key] += ';{}'.format(value)

        self.form = CaseInsensitiveDict()
        if 'x-www-form-urlencoded' in self.headers.get('Content-type', ''):
            for item in self.data.split('&', 2):
                k, v = item.split('=', 2)
                if k not in self.form:
                    self.form[k] = v
                else:
                    self.form[k] += ';{}'.format(v)

    def __str__(self):
        return '<Request: method={}, path={}, form={}, args={}>'.format(
            self.method,
            self.path,
            self.form,
            self.args,
        )

    def get_json(self):
        return self.json


class Response:
    # should follow https://flask.palletsprojects.com/en/1.1.x/api/#response-objects
    def __init__(self, body):
        self.body = body
        self.headers = CaseInsensitiveDict()
        self.status_code = 200

        # init
        self.headers['Content-Type'] = 'text/html'


def make_response(body):
    return Response(body=body)


patternTemplateVar = re.compile('\{\{(.+)\}\}')


def render_template(template_name, *args, **kwargs):
    with File('/templates/{}'.format(template_name), mode='rt') as file:
        ret = file.read()
        for match in patternTemplateVar.finditer(ret):
            key = match.group(1).strip()
            value = kwargs.get(key, '')
            if evalAvailable:
                try:
                    value = eval(key, kwargs)
                except Exception as e:
                    pass
                ret = ret.replace(match.group(0), str(value))

            else:
                ret = ret.replace(match.group(0), str(value))

    resp = make_response(ret)
    resp.headers['Content-Type'] = 'text/html'
    return resp


def jsonify(obj):
    resp = make_response(json.dumps(obj))
    resp.headers['content-type'] = 'application/json'
    return resp


try:
    # eval only works on XI processors
    eval('print("eval is available for templates")')
    evalAvailable = True
except Exception as e:
    print('eval() is not available', e)
    evalAvailable = False

if __name__ == "__main__":
    import datetime
    import random

    app = HTTP_Server(
        # debug=True
    )


    @app.route('/')
    def Index(request):
        return render_template('index.html')


    @app.route("/form", methods=["GET", "POST"])
    def Test(request):
        print('Test(request=', request)

        if request.form['username']:
            msg = 'Welcome {}'.format(request.form['username'])
        else:
            msg = ''

        return render_template(
            'form.html',
            message=msg
        )


    class Person:
        def __init__(self, name, age):
            self.name = name
            self.age = age


    @app.route('/template')
    def Template(request):
        person = Person(
            name=random.choice(['Grant', 'Joel', 'Matt', 'Anthony']),
            age=random.randint(21, 99)
        )
        return render_template(
            'template.html',
            name=person.name,
            currentTime=datetime.datetime.now(),
            person=person,
        )


    print('open a web browser to this machine\'s IP on port', app.IPPort, )
