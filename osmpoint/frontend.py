import flask
from flaskext.openid import OpenID
from wtforms import BooleanField, TextField, DecimalField, HiddenField
from wtforms import SelectField, Form, validators
from .database import db, Point
from .database import add_point, del_point, submit_points_to_osm


oid = OpenID()


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


frontend = flask.Blueprint('frontend', __name__)

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

def is_admin():
    return  flask.g.user in flask.current_app.config['OSMPOINT_ADMINS']

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
        flask.abort(403)

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
        flask.abort(403)

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
        flask.abort(403)

    form = flask.request.form
    point = Point.query.get_or_404(form['id'])

    if point.osm_id is not None:
        flask.abort(400)

    submit_points_to_osm(point)
    return flask.render_template('sent.html')

