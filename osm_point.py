import flask

from flaskext.sqlalchemy import SQLAlchemy

DEBUG = True
SQLALCHEMY_DB = "sqlite:///:memory:"

app = flask.Flask(__name__)
app.config.from_object(__name__)
db = SQLAlchemy(app)

class Point(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    name = db.Column(db.String(200))

    def __init__(self, latitude, longitude, name):
        self.latitude = latitude
        self.longitude = longitude
        self.name = name

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.name)


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
