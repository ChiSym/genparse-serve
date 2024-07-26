from flask import Flask, render_template, request, Response
import subprocess
import os
from functools import wraps

"""
To restart this app: sudo systemctl restart restart-service-app.service
"""

app = Flask(__name__)

SERVICE_NAME = 'genparse-server-app'
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)  
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/restart', methods=['POST'])
@requires_auth
def restart_service():
    try:
        result = subprocess.run(['/usr/bin/sudo', 'systemctl', 'restart', f'{SERVICE_NAME}.service'],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return f'Service {SERVICE_NAME} restarted successfully!', 200
    except subprocess.CalledProcessError as e:
        return f'Error restarting service: {e.stderr.decode()}', 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=9999)