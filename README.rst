GS HTTP Server
==============

A simple HTTP server that can be hosted by an Extron Pro Extron Processor.

Note: Extron's ControlScript added the SSLWrap() method which allows the processor to create a SSL server, but no effort has been made at this time to update this module to support HTTPS. (If you have any ideas on how to do that, feel free to send a Pull Request).

Simple Example Server
=====================

A basic HTTP server that accepts GET and POST request.
Also showing how to parse form data.

::

    import time
    from gs_http_server import HTTP_Server
    from extronlib.device import ProcessorDevice

    proc = ProcessorDevice('ProcessorAlias')
    server = HTTP_Server(proc=proc) # passing the processor is needed so the HTTP_Server knows the host IP


    # A simple HTTP GET that returns the current time.
    @server.route('/')
    def Index():
        return 'Hello. The current time is {}'.format(time.asctime()), 200
        # notice you can return the HTTP STATUS CODE (see https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
        # you can also just return the string (withouth the status code) like ' return "OK" '

    @server.route('/form', methods=['GET', 'POST'])
    def Post(*args, **kwargs):
        print('args={}, kwargs={}'.format(args, kwargs))
        method = kwargs.get('method')

        if method == 'POST':
            data = kwargs.get('data', {})
            print('type(data)=', type(data))
            return 'You posted "{}"'.format(data), 200

        elif method == GET
            return 'You can send JSON data in the HTTP Body. Try it using https://www.postman.com or a similar tool.', 200


    # you can also capture values in the url
    @server.route('/endpoint/<key>/<value>')
    def Endpoint(*args, **kwargs):
        print(args, kwargs)
        return 'You sent: key={}, value={}'.format(kwargs['key'], kwargs['value']), 200

    # you can also send params in the url
    # example http://server.com?key=value&key2=value2
    @server.route('/query_parameters')
    def QueryParams(*args, **kwargs):
        return 'You sent params={}'.format(kwargs['params'])

    print('Server Listening at http://{}:{}'.format(server.IPAddress, server.IPPort))
    # >>> Server Listening at http://10.20.30.40:5505

Testing using the python-requests package (https://pypi.org/project/requests/) or GS_Requests (https://github.com/GrantGMiller/gs_requests)

::

    import gs_requests as requests # Extron's Global Scripter
    # import requests # pc (windows/mac/linux)

    host = 'http://10.20.30.40:5505/'

    resp = requests.get(host)
    print('resp.text=', resp.text)
    # >>> Hello. The current time is Mon Nov 29 09:51:09 2021

    # send a post request
    resp = requests.post(host + 'form', json={'key1': 'value1', 'key2': 'value2'})
    print('resp.text=', resp.text)
    # >>> You posted "{'key1': 'value1', 'key2': 'value2'}"

    # send values in the url itself
    resp = requests.get(host + 'endpoint/start/room101')
    print('resp.text=', resp.text)
    # >>> You sent: key=start, value=room101

    # send values in the url parameters
    resp = requests.get(host + 'query_parameters', params={'paramKey1': 'paramValue2', 'paramKey2': 'paramValue2')
    print('resp.text=', resp.text)
    # >>> You sent params={'paramKey1': 'paramValue1', 'paramKey2': 'paramValue2'}