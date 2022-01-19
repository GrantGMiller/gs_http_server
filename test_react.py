import datetime

from gs_http_server import HTTP_Server, render_template, make_response
import random

app = HTTP_Server(
    debug=True
)


@app.route('/')
def Index(request):
    return make_response('''<html>
    <head>
        <script crossorigin src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"></script>
   
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body>
    <div id="react_container"></div>
    
    <script>
    const e = React.createElement;
    
    ReactDOM.render(
      e('div', null, 'Hello World'),
      document.querySelector("#react_container")
    );
    </script>
    
    </body></html>''')





print('open a web browser to', app.url )

