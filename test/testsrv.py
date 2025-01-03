from flask import Flask
import time

app = Flask(__name__)


@app.route('/', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
@app.route('/<path>', methods = ["GET", "POST", "DELETE", "HEAD", "PUT", "OPTIONS"])
def main(path):
	time.sleep(1)
	return "Success", 200

app.run()