import time
from gs_http_server import HTTP_Server
from extronlib.device import ProcessorDevice

proc = ProcessorDevice('ProcessorAlias')
server = HTTP_Server(proc=proc, debug=True)


@server.route('/')
def Index():
    return 'Hello. The current time is {}'.format(time.asctime()), 200


@server.route('/form', methods=['GET', 'POST'])
def Post(*args, **kwargs):
    print('args={}, kwargs={}'.format(args, kwargs))
    method = kwargs.get('method')

    if method == 'POST':
        data = kwargs.get('data', {})
        print('type(data)=', type(data))
        return 'You posted "{}"'.format(data), 200
    else:
        return 'You can send JSON data in the HTTP Body. Try it using https://www.postman.com or a similar tool.', 200


@server.route('/endpoint/<key>/<value>')
def Endpoint(*args, **kwargs):
    print(args, kwargs)
    return 'You sent: key={}, value={}'.format(kwargs['key'], kwargs['value']), 200


@server.route('/query_parameters')
def QueryParams(*args, **kwargs):
    return 'You sent params={}'.format(kwargs['params'])


print('Server Listening at http://{}:{}'.format(server.IPAddress, server.IPPort))
