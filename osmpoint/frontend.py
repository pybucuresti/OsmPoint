import flask
import yaml
import os
from flaskext.openid import OpenID
from wtforms import BooleanField, TextField, FloatField, HiddenField
from wtforms import SelectField, Form, validators
from .database import db, Point
from .database import add_point, del_point, submit_points_to_osm
import database


oid = OpenID()


class EditPointForm(Form):
    name = TextField('name', [validators.Required()])
    url = TextField('url')
    lat = FloatField('lat', [validators.NumberRange(min=-90, max=90)])
    lon = FloatField('lon', [validators.NumberRange(min=-180, max=180)])

    ops_file = os.path.join(os.path.dirname(__file__), 'amenities.yaml')
    options = yaml.load(file(ops_file, 'r'))
    for i, j in enumerate(options):
        options[i] = tuple(options[i])
    amenity = SelectField('amenity', choices=options)

    new_amenity = TextField('new_amenity')
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
    if flask.g.user is None:
        return flask.abort(400)
    del flask.session['openid']
    return flask.redirect('/')

@oid.after_login
def create_or_login(resp):
    flask.session['openid'] = resp.identity_url
    return flask.redirect(oid.get_next_url())

@frontend.route("/addPOI")
def init():
    if flask.g.user is None:
        return flask.redirect('/login?next=/addPOI')
    return flask.render_template('add_poi.html')

@frontend.route("/save_poi", methods=['POST'])
def save_poi():
    if flask.g.user is None:
        return flask.redirect('/login')

    form = EditPointForm(flask.request.form)

    if form.validate():
        if form.amenity.data == '_other' and form.new_amenity.data == "":
            ok_type = False

        else:
            if form.amenity.data == '_other':
                amenity = '#' + form.new_amenity.data

            else:
                amenity = form.amenity.data

            add_point(form.lat.data, form.lon.data, form.name.data,
                      form.url.data, amenity, flask.g.user)
            new_point = { 'latitude': form.lat.data,
                          'longitude': form.lon.data,
                          'marker': marker_for_amenity(amenity),
                          'name': form.name.data,
                          'type': amenity }

            return flask.render_template('thank_you.html', new_point=new_point)

    try:
        if ok_type is False:
            pass
    except UnboundLocalError:
        ok_type = form.amenity.validate(form)

    ok_name = form.name.validate(form)
    ok_coords = form.lat.validate(form) and form.lon.validate(form)
    return flask.render_template('edit.html', ok_coords=ok_coords,
                                 ok_name=ok_name, ok_type=ok_type)


@frontend.route("/about")
def about():
    return flask.render_template('info.html')

def marker_for_amenity(amenity):
    if amenity in ['pub', 'cafe', 'bar', 'fuel', 'nightclub',
                   'restaurant', 'theatre', 'cinema']:
        return amenity + '.png'
    else:
        return 'marker-blue.png'

def points_for_homepage():
    point_data = []

    osm_point_ids = set()

    for p_id, p in database.get_all_points():
        point_data.append({
            'latitude': p['lat'],
            'longitude': p['lon'],
            'marker': marker_for_amenity(p['amenity']),
            'name': p['name'],
            'type': p['amenity'],
        })
        if p['osm_id'] is not None:
            osm_point_ids.add(p['osm_id'])

    for p in flask.current_app.config['IMPORTED_POINTS']:
        if p['osm_id'] in osm_point_ids:
            continue
        osm_point_ids.add(p['osm_id'])
        point_data.append({
            'latitude': p['lat'],
            'longitude': p['lon'],
            'marker': marker_for_amenity(p['amenity']),
            'name': p['name'],
            'type': p['amenity'],
        })

    return point_data

@frontend.route("/")
def homepage():
    point_data = points_for_homepage()
    return flask.render_template('explore.html', point_data=point_data)

@frontend.route("/points")
def show_points():
    local_points = []
    sent_points = []
    for p_id, point in database.get_all_points():
        point['id'] = p_id
        if point['osm_id'] is None:
            local_points.append(point)
        else:
            sent_points.append(point)

    return flask.render_template('points.html',
                                 local_points=local_points,
                                 sent_points=sent_points)

@frontend.route("/points/<int:point_id>/delete", methods=['POST'])
def delete_point(point_id):
    point = database.get_point_or_404(point_id)

    if not is_admin():
        flask.abort(403)

    form = flask.request.form
    if form.get('confirm', None) == "true":
        del_point(point_id)
        point['id'] = point_id
        return flask.render_template('deleted.html', confirm=True, point=point)

    else:
        address = flask.url_for('.show_map', point_id=p_id)
        return flask.redirect(address)

@frontend.route("/points/<int:point_id>")
def show_map(point_id):
    point = database.get_point_or_404(point_id)
    point['id'] = point_id

    return flask.render_template('view.html', point=point,
                                  is_admin=is_admin())


@frontend.route("/points/<int:point_id>/edit", methods=['POST'])
def edit_point(point_id):
    form = EditPointForm(flask.request.form)
    point = Point.query.get_or_404(form.id.data)

    if not is_admin():
        flask.abort(403)

    if form.validate():
        if form.amenity.data == '_other' and form.new_amenity.data == "":
            ok_type = False
        else:
            if form.amenity.data == '_other':
                form.amenity.data = form.new_amenity.data
            form.populate_obj(point)
            point.latitude = form.lat.data
            point.longitude = form.lon.data

            db.session.add(point)
            db.session.commit()
            return flask.render_template('edit.html', ok_coords=1,
                                         ok_name=1, ok_type=1, id=point.id)

    try:
        if ok_type is False:
            pass
    except UnboundLocalError:
        ok_type = form.amenity.validate(form)

    ok_name = form.name.validate(form)
    ok_coords = form.lat.validate(form) and form.lon.validate(form)
    return flask.render_template('edit.html', ok_coords=ok_coords,
                                 ok_name=ok_name, ok_type=ok_type, id=point.id)

@frontend.route("/points/<int:point_id>/send", methods=['POST'])
def send_point(point_id):
    if not is_admin():
        flask.abort(403)

    point = database.get_point_or_404(point_id)
    if point['osm_id'] is not None:
        flask.abort(400)

    submit_points_to_osm([point_id])
    return flask.render_template('sent.html', id=point_id)

@frontend.route("/moderate", methods=['GET', 'POST'])
def moderate_view():
    if not is_admin():
        flask.abort(403)

    if flask.request.method == 'POST':
        point_id_list = [int(p_id) for p_id in
                         flask.request.form.getlist('point_id')]

        submit_points_to_osm(point_id_list)

        text = "%d points uploaded to OSM" % len(point_id_list)
        return flask.render_template('message.html', text=text)

    point_dict = lambda p: {
        'id': p.id,
        'latitude': p.latitude,
        'longitude': p.longitude,
        'marker': marker_for_amenity(p.amenity),
        'name': p.name,
        'type': p.amenity,
    }

    form_data = {
        'points': [point_dict(p) for p in
                   Point.query.filter(Point.osm_id==None)],
    }
    return flask.render_template('moderate.html', **form_data)

@frontend.route("/feedback", methods=['GET', 'POST'])
def feedback_view():
    if flask.request.method == 'POST':
        from mails import send_feedback_mail
        send_feedback_mail(flask.request.form['text'])
        text = "Thank you for your feedback"
        return flask.render_template('message.html', text=text)

    else:
        return flask.render_template('feedback.html')
