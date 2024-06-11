import logging
from flask import Flask
app = Flask(__name__, static_folder='../static')

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    logging.info("Here1")
    return app.send_static_file('index.html')

@app.route('/foo')
def foo():

    return "hello, world"

if __name__ == '__main__':
    app.run(debug=True)