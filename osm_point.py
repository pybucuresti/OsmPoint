import flask
app = flask.Flask(__name__)

@app.route("/")
def hello():
    return flask.render_template('home.html')

def main():
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
