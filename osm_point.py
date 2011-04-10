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

db.create_all()

def add_point(latitude, longitude, name):
    point = Point(latitude, longitude, name)
    db.session.add(point)
    db.session.commit()

@app.route("/")
def hello():
    return flask.render_template('home.html')

@app.route("/save_poi", methods=['POST'])
def save_poi():
    form = flask.request.form
    add_point(form['lat'], form['lon'], form['name'])
    return 'ok'

def main():
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
