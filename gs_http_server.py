# get the latest version of this module here:
# https://github.com/GrantGMiller/gs_http_server

import re
import json
import uuid
from collections import defaultdict
import datetime
import time
from extronlib import event
from urllib.parse import unquote
from extronlib.system import File, RFile
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
            self.print(type(self), 'running at', self.url)
        except:
            pass

    @property
    def url(self):
        return 'http://{}:{}/'.format(self.IPAddress, self.IPPort)

    @property
    def IPAddress(self):
        if self.proc is not None:
            return self.proc.IPAddress
        else:
            try:
                import socket  # only works on Q/XI processors
                return socket.gethostbyname(
                    socket.gethostname(),
                )
            except:
                return 'localhost'

    @property
    def IPPort(self):
        return self.serv.IPPort

    @staticmethod
    def BuildRoutePatterns(route):
        route_regex = re.sub(r"(<\w+>)", r"(?P\1[^\?]+)", route)
        return re.compile("^{}$".format(route_regex), re.IGNORECASE)

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
        '''
        Look up the view function by the path
        :param path:
        :return:
        '''
        splits = path.split("?")
        path = splits[0]

        for route_pattern, methods, view_function in self.routes:
            m = route_pattern.match(path)
            if m:
                kwargs = defaultdict(lambda: None)
                kwargs.update(m.groupdict())  # kwargs are from url matches like '/getuser/<name>'
                return kwargs, methods, view_function

        return None

    def print(self, *a, **k):
        if self.debug:
            print(*a, **k)

    def Serve(self, request):
        '''

        :param request:
        :return: Response obj
        '''
        self.print('87 req=', request)
        route_match = self.GetRouteMatch(request.path)
        self.print(71, route_match)
        if route_match:
            kwargs, methods, view_function = route_match

            self.print(73, kwargs, methods, view_function)
            if request.method in methods:
                # the view_function can accept several different arguments
                # try them all until one succeeds or all fail
                exception = None

                tmp = kwargs.copy()
                tmp.update({'request': request})
                for combo in [
                    tmp,
                    {'request': request},
                    kwargs.copy(),
                    dict(),
                ]:
                    self.print('combo=', combo)
                    try:
                        return self._FixViewFuncReturnType(
                            view_function(**combo),
                        )
                    except Exception as e:
                        self.print('Exception 122:', e, 'type=', type(e))
                        if exception is None:
                            exception = e
                        elif 'unexpected keyword argument' in str(e):
                            pass
                        elif 'missing 1 required positional argument' in str(e):
                            pass
                        elif 'argument after ** must be a mapping' in str(e):
                            pass
                        else:
                            exception = e
                else:
                    self.print('all combos failed. exception=', exception)
                    self.print('request=', request)
                    raise exception if exception else Exception('Erro 141: {}'.format(e))
            else:
                return make_response(
                    'Error 145: method "{}" not supported for this endpoint. Supported methods={}'.format(
                        request.method,
                        methods,
                    ), status_code=403)
        else:
            return make_response('Error 93: Route "{}"" has not been registered'.format(
                request.path), 404)

    @staticmethod
    def _FixViewFuncReturnType(ret):
        # the view function should return a str, tuple or Response object
        # if it returned a non-tuple, assume the user is implying a successfull
        # response ('ok', 200)
        if isinstance(ret, tuple):
            response = make_response(ret[0])
            response.status_code = ret[1]
            return response

        elif isinstance(ret, str):
            return make_response(ret)

        elif isinstance(ret, Response):
            return ret

        else:
            raise TypeError('Unrecognized return type "{}" from view function. ret={}'.format(
                type(ret),
                ret
            ))

    @staticmethod
    def StatusCode(status):
        codes = {
            200: "Ok",
            201: "Processed",
            302: "Redirect",
            304: "NOT MODIFIED",
            401: "Unauthorized",
            404: "Unavailable",
            500: 'Server Error',
        }
        return codes.get(status, 'Unkonwn Status Code {}'.format(status))

    # This receives the raw HTTP request
    def DataProcess(self, client, data):
        self.print('156', client, data)
        request = Request(raw=data, client=client)
        self.print('157 req=', request)
        try:
            response = self.Serve(request)
        except Exception as e:
            self.print('163 e=', e)
            response = jsonify({'Error 185': str(e)})
            response.status_code = 500

        self.DataReturn(client, response)
        return response

    def DataReturn(self, client, response):
        '''

        :param client:
        :param response: Response object
        :return:
        '''
        # This is last in the sequence. It actually sends the raw response back to the client.
        self.print('DataReturn(client=', client, ', response=', response)
        # change the Response object into a raw HTTP response
        response_headers = response.headers.copy()
        response_body_raw = response.body

        response_headers_raw = "".join(
            "{}: {}\r\n".format(k.capitalize(), v) for k, v in response_headers.items()
        )

        response_proto = response.proto
        response_status = response.status_code
        response_status_text = self.StatusCode(response.status_code)

        # sending the raw http response over the raw TCP connection
        try:
            client.Send(
                "{} {} {}\r\n".format(
                    response_proto,
                    response_status,
                    response_status_text))

            client.Send(response_headers_raw)
            # to separate headers from body
            # (https://stackoverflow.com/questions/5757290/http-header-line-break-style#5757349)
            client.Send("\r\n")

            data = response_body_raw.encode(encoding='iso-8859-1')
            client.Send(data)

        except Exception as e2:
            self.print("Exception 188:", e2)

    def _InitServerEvents(self):
        @event(self.serv, "ReceiveData")
        def HandleReceiveData(client, data):
            self.print(
                "HandleReceiveData({}, {}".format(
                    client, data.decode()))
            response = self.DataProcess(client, data.decode())
            try:
                if response.close_after_send:
                    client.Disconnect()
            except Exception as e:
                print("{} Exception 207:".format(type(self).__name__), e)

        @event(self.serv, ["Connected", "Disconnected"])
        def HandleClientConnect(client, state):
            self.print("Client {} ({}).".format(state, client.IPAddress))

        @self.route('/static/<filename>')
        def Static(filename, request):
            '''
            This will server static files that are located in the SFTP /static directory,
                or in the RFile space.

            :param filename:
            :param request:
            :return:
            '''
            print('Static(filename=', filename, ', request=', request)
            filename = unquote(filename)
            path = '/static/{}'.format(filename)
            if File.Exists(path):
                cls = File
            elif RFile.Exists(filename):
                cls = RFile
                path = filename
            else:
                cls = None

            if cls:
                with cls(path, mode='rb') as file:
                    resp = make_response(file.read().decode(encoding='iso-8859-1'))

                    resp.headers['Content-Disposition'] = 'inline; filename={}'.format(filename)
                    resp.headers['Cache-Control'] = 'no-cache'
                    resp.headers['Date'] = datetime.datetime.utcnow().strftime(
                        '%a, %d %b %Y %H:%M:%S GMT'
                    )
                    resp.headers['Last-Modified'] = resp.headers['Date']
                    resp.headers['Etag'] = '"{}"'.format(str(uuid.uuid4()))
                    typeMap = {
                        'jpg': 'image',
                        'png': 'image',
                        'jpeg': 'image',
                        'gif': 'image',
                        'jfif': 'image',
                        'ico': 'image',

                        'flv': 'video',
                        'mov': 'video',
                        'mp4': 'video',
                        'wmv': 'video',

                        'mp3': 'audio',
                        'wav': 'audio',
                        'm4a': 'audio',
                    }
                    extension = filename.split('.')[-1]
                    resp.headers['Content-Type'] = '{}/{}'.format(
                        typeMap.get(extension.lower(), 'image'),
                        extension,
                    )

                    resp.headers.pop('connection', None)
                    resp.headers.pop('Content-Language', None)

                    resp.status_code = 200
                    resp.proto = 'HTTP/1.0'
                    resp.close_after_send = True
                    return resp
            else:
                return 'File "{}" not found in "/static" sftp directory or RFile space'.format(filename), 404


class HTTPS_Server(HTTP_Server):
    # WIP - still have to figure out how to make the IPCP trust my PC's certs
    def __init__(self,
                 certificate,
                 ca_certs,
                 cert_reqs='CERT_NONE',
                 ssl_version='TLSv2',
                 proc=None, port=5505, debug=False,
                 ):

        self.proc = proc

        self.debug = debug
        self.defaultMethods = ["GET"]
        self.routes = []  # list of tuples [(pattern, methods, callback), ...]
        # Starts the Server Instance
        self.serv = EthernetServerInterfaceEx(port, "TCP")
        self.serv.SSLWrap(
            certificate=certificate,
            cert_reqs=cert_reqs,
            ssl_version=ssl_version,
            ca_certs=ca_certs,
        )
        self.print("self.serv=", self.serv)
        res = self.serv.StartListen()
        if res != "Listening":
            print("self.serv.StartListen() res=", res)
            # this is not likely to recover
            raise ResourceWarning("Port unavailable")
        self._InitServerEvents()
        try:
            self.print(type(self), 'running at', self.url)
        except:
            pass

    @property
    def url(self):
        return 'https://{}:{}/'.format(self.IPAddress, self.IPPort)


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

    def pop(self, k, *args, **kwargs):
        return super().pop(k.lower(), *args, **kwargs)


class Request:
    # should follow https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
    def __init__(self, raw, **kwargs):
        self.raw = NormalizeLineEndings(raw)
        self.client = kwargs.pop('client', None)

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
                v = unquote(v)
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
        return '<Request: method={}, path={}, form={}, args={}, client={}>'.format(
            self.method,
            self.path,
            self.form,
            self.args,
            self.client,
        )

    def get_json(self):
        return self.json


class Response:
    # should follow https://flask.palletsprojects.com/en/1.1.x/api/#response-objects
    def __init__(self, body):
        self.body = body
        self.headers = CaseInsensitiveDict()
        self.status_code = 200
        self.proto = 'HTTP/1.1'
        self.close_after_send = True

        # init
        self.headers['Content-Type'] = 'text/html'
        self.headers['connection'] = 'close'
        self.headers[
            'Content-Language'] = 'en-US'  # sometimes chrome will prompt the user with "view this page in english?" if you dont include this header
        self.headers['content-length'] = len(body)
        self.headers['Server'] = 'GS_HTTP_SERVER'

    def __str__(self):
        return '<Response: status_code={}, headers={}, body={}>'.format(
            self.status_code,
            self.headers,
            self.body
        )


def make_response(body='', status_code=200):
    resp = Response(body=body)
    resp.status_code = status_code
    return resp


def send_file(path):
    with File(path, mode='rb') as file:
        return file.read()


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
                if isinstance(value, Response):
                    value = value.body
                else:
                    ret = ret.replace(match.group(0), str(value))

    resp = make_response(ret)
    resp.headers['Content-Type'] = 'text/html'
    return resp


def jsonify(obj):
    resp = make_response(json.dumps(obj, indent=2))
    resp.headers['content-type'] = 'application/json'
    return resp


def redirect(url):
    # works like flask.redirect()
    # see https://flask.palletsprojects.com/en/1.1.x/api/
    resp = make_response()
    resp.headers['Location'] = url
    resp.status_code = 302
    return resp


try:
    # eval only works on XI processors
    eval('print("eval is available for templates")')
    evalAvailable = True
except Exception as e:
    print('eval() is not available', e)
    evalAvailable = False

if __name__ == "__main__":
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
