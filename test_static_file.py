import datetime

from gs_http_server import HTTP_Server, render_template, make_response
import random

app = HTTP_Server(
    debug=True
)


@app.route('/')
def Index(request):
    return make_response('''<html><body>
    <img src="/static/image.jpg">
    </body></html>''')





print('open a web browser to', app.url )

