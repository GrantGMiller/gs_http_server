import json
import time
from urllib.request import urlopen

# Example of Set
data = {'currentTime': time.asctime()}
resp = urlopen('http://10.8.254.78:5505/post', data=json.dumps(data).encode())
print('resp=', resp.read().decode())

# Example of Get
resp = urlopen('http://10.8.254.78:5505/')
print('resp=', resp.read().decode())