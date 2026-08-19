from flask import Flask, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import os, time, random

app = Flask(__name__)
REQUESTS = Counter('gary_app_requests_total', 'Total HTTP requests', ['endpoint'])
LATENCY = Histogram('gary_app_request_duration_seconds', 'Request latency', ['endpoint'])

@app.route('/')
def home():
    start=time.time(); REQUESTS.labels('/').inc()
    time.sleep(random.uniform(0.01,0.05))
    LATENCY.labels('/').observe(time.time()-start)
    msg=os.getenv('APP_MESSAGE','Gary Fang CSE644 Assignment 03 - GitOps v1')
    return f'<h1>{msg}</h1><p>Observable Python application on Kubernetes.</p>'

@app.route('/health')
def health():
    REQUESTS.labels('/health').inc(); return 'ok', 200

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
