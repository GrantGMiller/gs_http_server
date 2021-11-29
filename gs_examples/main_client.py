import time
import gs_requests as requests

# Example of HTTP POST
data = {'currentTime': time.asctime()}
resp = requests.post('http://192.168.68.105:5505/form', json=data)
print('resp.text=', resp.text)

# Example of HTTP GET
resp = requests.get('http://192.168.68.105:5505/')
print('resp.text=', resp.text)