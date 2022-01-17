from gs_http_server import HTTPS_Server, jsonify
import time
import extronlib
from extronlib.device import ProcessorDevice

try:
    extronlib.ExportForGS(r'C:\Users\gmiller\PycharmProjects\gs_http_server\gs_examples\temp')
except:
    pass

app = HTTPS_Server(
    certificate='ExtronMachine',  # You must load a "Machine Certificate" via toolbelt, this is the certificate 'alias'
    ca_certs='extron_enterprise_root',  # You must load a "CA Certificate" via toolbelt, this is the certificate 'alias'
    proc=ProcessorDevice('ProcessorAlias')
)


@app.route('/')
def Index():
    return jsonify('The time is {}'.format(time.asctime()))


print(app.url)
