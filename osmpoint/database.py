import logging
from flaskext.sqlalchemy import SQLAlchemy
import flask
import OsmApi

log = logging.getLogger(__name__)
db = SQLAlchemy()

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

def add_point(latitude, longitude, name, url, amenity, user_open_id):
    point = Point(latitude, longitude, name, url, amenity, user_open_id)
    db.session.add(point)
    db.session.commit()
    return point.id

def del_point(point):
    db.session.delete(point)
    db.session.commit()

def get_osm_api():
    osm_password_path = flask.current_app.config['OSM_PASSWORD_PATH']
    return OsmApi.OsmApi(passwordfile=osm_password_path)

def submit_points_to_osm(point_to_submit):
    osm = get_osm_api()
    osm._api = flask.current_app.config['OSM_API']
    changeset_id = osm.ChangesetCreate({u"comment": u"Submitted by OsmPoint"})
    log.info("Begin OSM changeset %d", changeset_id)
    for p in point_to_submit:
        node_dict = osm.NodeCreate({u"lon": p.longitude,
                                    u"lat": p.latitude,
                                    u"tag": {'name': p.name,
                                             'amenity': p.amenity,
                                             'website': p.url}})
        p.osm_id = node_dict['id']
        log.info("OSM point: %r", node_dict)
        db.session.add(p)
    osm.ChangesetClose()
    db.session.commit()
    log.info("OSM changeset committed")


# monkey patch SQLite so we can log statemets just as we like

def monkeypatch_method(cls):
    def decorator(func):
        old_func = getattr(cls, func.__name__, None)
        if old_func is not None:
            old_ref = "_original_%s" % func.__name__
            setattr(cls, old_ref, old_func)
            old_funcs = getattr(cls, old_ref, None)
        setattr(cls, func.__name__, func)
        return func
    return decorator

from sqlalchemy.engine.default import DefaultDialect

@monkeypatch_method(DefaultDialect)
def do_execute(self, cursor, statement, parameters, context=None):
    if any(statement.startswith(s) for s in ['INSERT ', 'UPDATE ', 'DELETE ']):
        log.info("%s %r", statement, parameters)
    return self._original_do_execute(cursor, statement, parameters, context)
