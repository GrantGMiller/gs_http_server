GS HTTP Server
==============

A simple HTTP server that can be hosted by an Extron Pro Extron Processor.
Inspired by https://flask.palletsprojects.com/en/2.0.x/

Note: Extron's ControlScript added the SSLWrap() method which allows the processor to create a SSL server, but no effort has been made at this time to update this module to support HTTPS. (If you have any ideas on how to do that, feel free to send a Pull Request).

Simple JSON API Server
======================

A basic HTTP server that accepts GET and POST request.
Also showing how to parse form data.

::

    import time
    from gs_http_server import HTTP_Server, jsonify
    from extronlib.device import ProcessorDevice

    proc = ProcessorDevice('ProcessorAlias')
    server = HTTP_Server(proc=proc)  # passing the processor is needed so the HTTP_Server knows the host IP


    # A simple HTTP GET that returns the current time.
    @server.route('/')
    def Index():
        return jsonify('Hello. The current time is {}'.format(time.asctime()))


    @server.route('/form', methods=['GET', 'POST'])
    def Post(request):
        print('Post(request=', request)

        if request.method == 'POST':
            return jsonify('You posted "{}"'.format(request.json))

        elif request.method == 'GET':
            return jsonify('You can send JSON data in the HTTP Body. Try it using https://www.postman.com or a similar tool.')


    # you can also capture values in the url
    @server.route('/endpoint/<key>/<value>')
    def Endpoint(request, key, value):
        print('Endpoint(request=', request)
        return jsonify('You sent: key={}, value={}'.format(key, value))


    # you can also send params in the url
    # example http://server.com?key=value&key2=value2
    @server.route('/query_parameters')
    def QueryParams(request):
        print('QueryParams(request=', request)
        return jsonify('You sent params={}'.format(request.args))


    print('Server Listening at http://{}:{}'.format(server.IPAddress, server.IPPort))
    # >>> Server Listening at http://10.20.30.40:5505

Templating Engine
=================
A simple templating engine to render web pages.
Inspired by https://jinja.palletsprojects.com/en/3.0.x/

::

    import datetime
    import random
    from gs_http_server import HTTP_Server, render_template

    app = HTTP_Server(
        # debug=True
    )


    # All template files should be in a directory called 'templates'
    @app.route('/')
    def Index():
        return render_template(
            'index.html'  # this file name is relative to the '/templates' directory
        )


    @app.route("/form", methods=["GET", "POST"])
    def Test(request):
        print('Test(request=', request)

        if request.method == 'POST' and request.form['username']:
            # the user submitted the form and entered their username, welcome them
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
            person=person, # the templating-engine can render object attributes or method calls, only available on Q/XI processors
        )


    print('open a web browser to this machine\'s IP on port', app.IPPort, )


Template Format
===============
The template file should be stored in a directory called 'templates'.
This is the 'template.html' for the example above.

::

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Title</title>
    </head>
    <body>
        Hello {{ name }},<br>
        The time is {{ currentTime }}.
        <br>
        name={{person.name}}
        <br>
        age={{person.age}}
    </body>
    </html>

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