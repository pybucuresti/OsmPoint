import flask

from flaskext.openid import OpenID
import OsmApi
from wtforms import BooleanField, TextField, DecimalField, HiddenField
from wtforms import SelectField, Form, validators

from osmpoint.database import db, Point
oid = OpenID()
from osmpoint.database import add_point, del_point, submit_points_to_osm

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

    try:
        with open(os.path.join(workdir, 'secret'), 'rb') as f:
            app.config['SECRET_KEY'] = f.read()
    except IOError:
        app.config['SECRET_KEY'] = None # TODO issue a warning in the log

    try:
       with open(os.path.join(workdir, 'admins'), 'r') as f:
           app.config['OSMPOINT_ADMINS'] = f.read().split()
    except IOError:
       app.config['OSMPOINT_ADMINS'] = []

    openid_path = os.path.join(workdir, 'openid_store')
    app.config['OPENID_FS_STORE_PATH'] = openid_path

    app.config['OSM_PASSWORD_PATH'] = os.path.join(workdir,'osm-login.txt')


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
