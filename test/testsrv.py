from flask import Flask, current_app
import time
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
setattr(app, "request_count", 0)

@app.route('/', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
@app.route('/<path>', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
def main(path):
	time.sleep(1)
	current_app.request_count += 1

	if current_app.request_count % 100 == 0:
		print(f"Request Count: {current_app.request_count}")
	return "Success", 200

app.run()