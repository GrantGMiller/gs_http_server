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


print('open a web browser to', app.url)
