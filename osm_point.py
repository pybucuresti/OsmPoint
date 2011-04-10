DEBUG = True

import flask
app = flask.Flask(__name__)
app.config.from_object(__name__)

@app.route("/")
def hello():
    return flask.render_template('home.html')

@app.route("/save_poi", methods=['POST'])
def save_poi():
    app.logger.debug('something happened')
    app.logger.debug("%r", flask.request)
    print flask.request.form["name"]
    return "whatever"

def main():
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
