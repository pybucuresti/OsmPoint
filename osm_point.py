import flask

from flaskext.sqlalchemy import SQLAlchemy
from flaskext.openid import OpenID

app = flask.Flask(__name__)
db = SQLAlchemy(app)
oid = OpenID(app)

def configure_app(workdir):
    import os.path
    workdir = os.path.abspath(workdir)

    app.config['DEBUG'] = True

    db_path = os.path.join(workdir, 'db.sqlite3')
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///%s" % db_path
    db.create_all()

    with open(os.path.join(workdir, 'secret'), 'rb') as f:
        app.config['SECRET_KEY'] = f.read()

    global oid
    openid_path = os.path.join(workdir, 'openid_store')
    app.config['OPENID_FS_STORE_PATH'] = openid_path

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

def add_point(latitude, longitude, name):
    point = Point(latitude, longitude, name)
    db.session.add(point)
    db.session.commit()

@app.before_request
def lookup_current_user():
    flask.g.user = None
    if 'openid' in flask.session:
        flask.g.user = "[openid %s]" % flask.session['openid']

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if flask.g.user is not None:
        return flask.redirect(oid.get_next_url())
    if flask.request.method == 'POST':
        openid = flask.request.form.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return flask.render_template('login.html',
                                 next=oid.get_next_url(),
                                 error=oid.fetch_error())

@app.route('/logout')
def logout():
    del flask.session['openid']
    return flask.redirect('/')

@oid.after_login
def create_or_login(resp):
    flask.session['openid'] = resp.identity_url
    #flask.g.user = "[openid %s]" % flask.session['openid']
    return flask.redirect('/')

@app.route("/")
def hello():
    app.logger.debug('user: %r', flask.g.user)
    return flask.render_template('home.html')

@app.route("/save_poi", methods=['POST'])
def save_poi():
    form = flask.request.form
    add_point(form['lat'], form['lon'], form['name'])
    return 'ok'

def main():
    import sys
    configure_app(sys.argv[1])
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
