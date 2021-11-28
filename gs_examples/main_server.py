import time

from gs_http_server import Rest_Server
from extronlib.device import ProcessorDevice

proc = ProcessorDevice('ProcessorAlias')
server = Rest_Server(proc=proc)


@server.route('/')
def Index():
    return 'Hello. The current time is {}'.format(time.asctime()), 200


@server.route('/post', methods=['GET', 'POST'])
def Post(*args, **kwargs):
    print('args={}, kwargs={}'.format(args, kwargs))
    method = kwargs.get('method')

    if method == 'POST':
        data = kwargs.get('data', {})
        return 'You posted "{}"'.format(data), 200
    else:
        return 'You can send JSON data in the HTTP Body. Try it.', 200


print('Server Listening at http://{}:{}'.format(server.IPAddress, server.IPPort))
