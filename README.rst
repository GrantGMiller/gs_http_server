GS HTTP Server
==============

A simple HTTP server that can be hosted by an Extron Pro Extron Processor.
Inspired by https://flask.palletsprojects.com/en/2.0.x/

Note: Extron's ControlScript added the SSLWrap() method which allows the processor to create a SSL server, but no effort has been made at this time to Update this module to support HTTPS. (If you have any ideas on how to do that, feel free to send a Pull Request).

Simple JSON API Server
======================

A basic HTTP server that accepts GET and POST request.
Also showing how to parse form data.

::

    import time
    from gs_http_server import HTTP_Server, jsonify
    from extronlib.device import ProcessorDevice

    proc = ProcessorDevice('ProcessorAlias')
    server = HTTP_Server(
        proc=proc,
        debug=True,
    )  # passing the 'proc' is optional, but will allow you to reference the host IP Address using 'server.IPAddress'


    # A simple HTTP GET that returns the current time.
    @server.route('/')
    def Index():
        return jsonify('Hello. The current time is {}'.format(time.asctime()))
        # jsonify formats the HTTP response data as a json object
        #   it also adds the 'Content-Type': 'application/json' header to the HTTP response


    @server.route('/form', methods=['GET', 'POST'])
    def Post(request):
        # the 'request' argument contains info about the HTTP Request that was received
        # Your View Function (in this case 'Post()') can accept a parameter called 'request' or not +
        # For example see 'Index()' above, notice it does not accept any parameters
        print('Post(request=', request)

        if request.method == 'POST':
            return jsonify('You posted "{}"'.format(request.json))

        elif request.method == 'GET':
            return jsonify(
                'You can send JSON data in the HTTP Body. Try it using https://www.postman.com or a similar tool.'
            )


    # you can also capture values in the url
    @server.route('/endpoint/<key>/<value>')
    def Endpoint(key, value):
        print('Endpoint(key=', key, ', value=', value)
        return jsonify('You sent: key={}, value={}'.format(key, value))


    # you can also send params in the url
    # example http://server.com?name=Bob&age=99
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

Static Files
============
Any files that are stored in the SFTP "/static" directory, or that are included in the RFile directory, can be served directly by directing the browser to '/static/<filename>'.

For example, if the file is named 'image.jpg' then you can include the image in a web page by adding

::

    <img src='/static/image.jpg'/>

Redirect
========
You can send the client to another page by using the redirect() function.
This creates a HTTP 302 redirect response.

::

    @app.route('/redirect_test')
    def RedirectTest():
        return redirect('/other_page')

    # You can also redirect to an outside URL
    @app.route('/go_to_google')
    def GoToGoogle():
        return redirect('https://google.com')

Cookies
=======
You can get the request cookies by accessing *request.cookies*
You can set the cookies on a response by calling *response.set_cookies(key, value)*

::

    import datetime
    import time

    from gs_http_server import HTTP_Server, render_template, make_response, redirect
    import random

    app = HTTP_Server(
        debug=True
    )


    @app.route('/')
    def Index(request):
        print('request=', request)
        resp = make_response('These are the cookies received from the browser: {}'.format(request.cookies))
        if not request.cookies:
            # there are not cookies, create a new one
            resp.set_cookie('Cookies Created At', time.asctime())
            # You'll notice that if you refresh the browser, the cookie does not change.
            # However if you open a private-browser window, a new cookie is created.
        return resp


    # In a real-world scenario, this can be used for things like the "Remember My Username" feature on a login page.
    # for example
    @app.route('/login', methods=['GET', 'POST'])
    def Login(request):
        print('request=', request)
        if request.method == 'GET':

            if 'username' in request.cookies:
                # this will pre-fill the login form with the username, which the user will appreciate
                return render_template('login.html', username=request.cookies['username'])
            else:
                return render_template('login.html', )

        elif request.method == 'POST':
            if request.form.get('username', None) == 'admin' and request.form.get('password', None) == 'password123':
                resp = redirect('/')
                resp.set_cookie('username', 'admin')
                # Now, anytime they visit the /login page, the username will be pre-filled
                return resp
            else:
                print('wrong username/password')
                return redirect('/login')


Testing
=======

Recommended testing tools:

python-requests (windows/linux): https://pypi.org/project/requests/

GS_Requests (Extron Controllers): https://github.com/GrantGMiller/gs_requests

Postman (windows/linux): https://www.postman.com/

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