import flask

from flaskext.sqlalchemy import SQLAlchemy
from flaskext.openid import OpenID
import OsmApi
from wtforms import BooleanField, TextField, DecimalField, HiddenField
from wtforms import SelectField, Form, validators

db = SQLAlchemy()
oid = OpenID()
osm = None

frontend = flask.Blueprint('frontend', __name__)

def configure_app(app, workdir):
    import os.path
    workdir = os.path.abspath(workdir)

    app.config['DEBUG'] = True
    app.config['STATIC_CACHE_TIMEOUT'] = 0

    db_path = os.path.join(workdir, 'db.sqlite3')
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///%s" % db_path
    with app.test_request_context():
        db.create_all()

    with open(os.path.join(workdir, 'secret'), 'rb') as f:
        app.config['SECRET_KEY'] = f.read()

    try:
       with open(os.path.join(workdir, 'admins'), 'r') as f:
           app.config['OSMPOINT_ADMINS'] = f.read().split()
    except IOError:
       app.config['OSMPOINT_ADMINS'] = []

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
    url = db.Column(db.String(50))
    amenity = db.Column(db.String(50))
    osm_id = db.Column(db.Integer)
    user_open_id = db.Column(db.Text)

    def __init__(self, latitude, longitude, name, url, amenity, user_open_id):
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
        self.url = url
        self.amenity = amenity
        self.user_open_id = user_open_id

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.name)

class EditPointForm(Form):
    name = TextField('name', [validators.Required()])
    url = TextField('url')
    lat = DecimalField('lat', [validators.NumberRange(min=-90, max=90)])
    lon = DecimalField('lon', [validators.NumberRange(min=-180, max=180)])
    amenity = SelectField('amenity', choices=[('bar', 'bar'), ('cafe', 'cafe'),
                                              ('fuel','fuel'),('pub','pub'),
                                              ('restaurant','restaurant'),
                                              ('nightclub','nightclub')]
                         )
    id = HiddenField('id', [validators.Optional()])

def add_point(latitude, longitude, name, url, amenity, user_open_id):
    point = Point(latitude, longitude, name, url, amenity, user_open_id)
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
                                    u"tag": {'name': p.name,
                                             'amenity': p.amenity,
                                             'website': p.url}})
        p.osm_id = node_dict['id']
        db.session.add(p)
    osm.ChangesetClose()
    db.session.commit()

def is_admin():
    return  flask.g.user in flask.current_app.config['OSMPOINT_ADMINS']

@frontend.before_request
def lookup_current_user():
    flask.g.user = None
    if 'openid' in flask.session:
        flask.g.user = flask.session['openid']

@frontend.route('/login', methods=['GET', 'POST'])
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

@frontend.route('/logout')
def logout():
    del flask.session['openid']
    return flask.redirect('/')

@oid.after_login
def create_or_login(resp):
    flask.session['openid'] = resp.identity_url
    return flask.redirect('/')

@frontend.route("/")
def homepage():
    return flask.render_template('home.html')

@frontend.route("/save_poi", methods=['POST'])
def save_poi():
    if flask.g.user is None:
        return flask.redirect('/login')

    form = EditPointForm(flask.request.form)

    if form.validate():
        add_point(form.lat.data, form.lon.data, form.name.data,
                  form.url.data, form.amenity.data, flask.g.user)
        return flask.redirect('/thank_you')

    ok_type = form.amenity.validate(form)
    ok_name = form.name.validate(form)
    ok_coords = form.lat.validate(form) and form.lon.validate(form)
    return flask.render_template('edit.html', ok_coords=ok_coords,
                                 ok_name=ok_name, ok_type=ok_type)


@frontend.route("/thank_you")
def thank_you():
    return flask.render_template('thank_you.html')

@frontend.route("/points")
def show_points():
    local_points = Point.query.filter(Point.osm_id==None).all()
    sent_points = Point.query.filter(Point.osm_id!=None).all()

    return flask.render_template('points.html',
                                 local_points=local_points,
                                 sent_points=sent_points)

@frontend.route("/points/<int:point_id>/delete", methods=['POST'])
def delete_point(point_id):
    form = flask.request.form
    point = Point.query.get_or_404(form['id'])

    if not is_admin():
        flask.abort(404)

    del_point(point)
    return flask.render_template('deleted.html')

@frontend.route("/points/<int:point_id>")
def show_map(point_id):
    point = Point.query.get_or_404(point_id)

    return flask.render_template('view.html', point=point,
                                  is_admin=is_admin())


@frontend.route("/points/<int:point_id>/edit", methods=['POST'])
def edit_point(point_id):
    form = EditPointForm(flask.request.form)
    point = Point.query.get_or_404(form.id.data)

    if not is_admin():
        flask.abort(404)

    if form.validate():

        form.populate_obj(point)
        point.latitude = form.lat.data
        point.longitude = form.lon.data

        db.session.add(point)
        db.session.commit()
        return flask.render_template('edit.html', ok_coords=1,
                                     ok_name=1, ok_type=1)

    ok_type = form.amenity.validate(form)
    ok_name = form.name.validate(form)
    ok_coords = form.lat.validate(form) and form.lon.validate(form)
    return flask.render_template('edit.html', ok_coords=ok_coords,
                                 ok_name=ok_name, ok_type=ok_type)

@frontend.route("/points/<int:point_id>/send", methods=['POST'])
def send_point(point_id):
    if not is_admin():
        flask.abort(404)

    form = flask.request.form
    point = Point.query.get_or_404(form['id'])

    if point.osm_id is not None:
        flask.abort(400)

    submit_points_to_osm(point)
    return flask.render_template('sent.html')


def create_app(workdir):
    app = flask.Flask(__name__)
    db.init_app(app)
    oid.init_app(app)

    app.register_blueprint(frontend)

    configure_app(app, workdir)

    return app
