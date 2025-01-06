from flask import Flask, current_app
import time
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
setattr(app, "request_counter_total", 0)
setattr(app, "request_counter", 0)
setattr(app, "last_request_time", 0)
@app.route('/<path>', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
@app.route('/', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
def main(path):
	time.sleep(1)
	current_app.request_counter_total += 1
	current_app.request_counter += 1

	if current_app.request_counter_total % 10000 == 0:
		print(f"Request Count: {current_app.request_counter_total}")
		current_time  = time.time()

		time_since_last = current_time - current_app.last_request_time

		req_per_sec = current_app.request_counter / time_since_last

		print(f"{req_per_sec}/s")
		current_app.last_request_time = current_time
		current_app.request_counter = 0

	return "Success", 200


@app.route('/reset_stats_counters', methods = ["GET"])
def reset():
	current_app.request_counter_total = 0
	current_app.last_request_time = 0

app.run()