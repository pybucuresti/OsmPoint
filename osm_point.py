import flask

from flaskext.sqlalchemy import SQLAlchemy
from flaskext.openid import OpenID
import OsmApi

app = flask.Flask(__name__) # TODO split away a module with the views
db = SQLAlchemy(app)
oid = OpenID(app)
osm = None

def configure_app(workdir):
    import os.path
    workdir = os.path.abspath(workdir)

    app.config['DEBUG'] = True

    db_path = os.path.join(workdir, 'db.sqlite3')
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///%s" % db_path
    db.create_all()

    with open(os.path.join(workdir, 'secret'), 'rb') as f:
        app.config['SECRET_KEY'] = f.read()

    try:
       with open(os.path.join(workdir, 'admins'), 'r') as f:
           app.config['OSMPOINT_ADMINS'] = f.read().split()
    except IOError:
       app.config['OSMPOINT_ADMINS'] = None

    global oid
    openid_path = os.path.join(workdir, 'openid_store')
    app.config['OPENID_FS_STORE_PATH'] = openid_path

    global osm
    osm_password_path = os.path.join(workdir,'osm-login.txt')
    if os.path.isfile(osm_password_path):
        osm = OsmApi.OsmApi(passwordfile=osm_password_path)

class Point(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    name = db.Column(db.String(200))
    osm_id = db.Column(db.Integer)
    user_open_id = db.Column(db.Text)

    def __init__(self, latitude, longitude, name, user_open_id):
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
        self.user_open_id = user_open_id

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.name)

def add_point(latitude, longitude, name, user_open_id):
    point = Point(latitude, longitude, name, user_open_id)
    db.session.add(point)
    db.session.commit()

def del_point(point):
    db.session.delete(point)
    db.session.commit()

def submit_points_to_osm(point_to_submit):
    osm.ChangesetCreate({u"comment": u"Submitted by OsmPoint"})
    for p in point_to_submit:
        node_dict = osm.NodeCreate({u"lon": p.longitude,
                                    u"lat": p.latitude,
                                    u"tag": {'name': p.name}})
        p.osm_id = node_dict['id']
        db.session.add(p)
    osm.ChangesetClose()
    db.session.commit()

def coords(lat, lon):
    lat = float(lat)
    lon = float(lon)
    if (lat < -90 or lat > 90):
        return False
    if (lon < -180 or lon > 180):
        return False
    return True

def is_admin():
    try:
        return  bool(flask.g.user in app.config['OSMPOINT_ADMINS'])
    except TypeError:
        return False

@app.before_request
def lookup_current_user():
    flask.g.user = None
    if 'openid' in flask.session:
        flask.g.user = flask.session['openid']

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
    return flask.redirect('/')

@app.route("/")
def homepage():
    logged_in = bool(flask.g.user is not None)
    return flask.render_template('home.html', logged_in=logged_in)

@app.route("/save_poi", methods=['POST'])
def save_poi():
    logged_in = bool(flask.g.user is not None)
    if not logged_in:
        return flask.redirect('/login')

    form = flask.request.form

    if coords(form['lat'], form['lon']):
        add_point(form['lat'], form['lon'], form['name'], flask.g.user)
        return flask.redirect('/thank_you')

    return flask.redirect('/')


@app.route("/thank_you")
def thank_you():
    return flask.render_template('thank_you.html')

@app.route("/points")
def show_points():
    local_points = Point.query.filter(Point.osm_id==None).all()
    sent_points = Point.query.filter(Point.osm_id!=None).all()

    return flask.render_template('points.html',
                                 local_points=local_points,
                                 sent_points=sent_points)

@app.route("/delete", methods=['POST'])
def delete_point():
    form = flask.request.form
    point = Point.query.get_or_404(form['id'])

    if point is 404 or is_admin() is False:
        flask.abort(404)

    del_point(point)
    return flask.render_template('deleted.html')

# TODO URL scheme: /point/1, /point/1/save, /point/1/delete, /point/1/submit
@app.route("/view")
def show_map():
    point = Point.query.get_or_404(flask.request.args['id'])

    if point is 404:
        flask.abort(404) # TODO test me
    return flask.render_template('view.html', point=point,
                                  is_admin=is_admin())

@app.route("/send", methods=['POST'])
def send_point():
    if is_admin() is False:
        flask.abort(404)

    form = flask.request.form
    point = Point.query.get_or_404(form['id'])

    if point is 404:
       flask.abort(404)

    if point.osm_id is not None:
        flask.abort(404)

    if coords(form['lat'], form['lon']):
        point.latitude = form['lat']
        point.longitude = form['lon']

    point.name = form['name']
    db.session.add(point)
    db.session.commit()
    submit_points_to_osm(point)
    return flask.render_template('sent.html')

def main():
    import sys
    configure_app(sys.argv[1])
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
