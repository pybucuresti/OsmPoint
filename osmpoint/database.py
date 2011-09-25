import logging
from flaskext.sqlalchemy import SQLAlchemy
import flask
import OsmApi
import flatland as fl

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
    app = flask.current_app
    return OsmApi.OsmApi(api=app.config['OSM_API'],
                         passwordfile=app.config['OSM_PASSWORD_PATH'])

def submit_points_to_osm(point_to_submit):
    osm = get_osm_api()
    osm._api = flask.current_app.config['OSM_API']
    changeset_id = osm.ChangesetCreate({u"comment": u"Submitted by OsmPoint"})
    log.info("Begin OSM changeset %d", changeset_id)

    for p in point_to_submit:
        tags = {
            'name': p.name,
            'amenity': p.amenity,
            'source': "poi.grep.ro",
        }
        if p.url:
            tags['website'] = p.url

        node_dict = osm.NodeCreate({
            u"lon": p.longitude,
            u"lat": p.latitude,
            u"tag": tags,
        })

        p.osm_id = node_dict['id']
        db.session.add(p)
        log.info("OSM point: %r", node_dict)

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


class PointModel(fl.Form):
    lat = fl.Float
    lon = fl.Float


class RedisDb(object):
    model = {
        'point': PointModel,
    }

    def __init__(self, sock_path):
        from redis import Redis
        self._r = Redis(unix_socket_path=sock_path)

    def add(self, name, data):
        ob_id = self._r.incr('%s:next_id' % name)
        return self.put(name, ob_id, data)

    def put(self, name, ob_id, data):
        model_cls = self.model[name]
        model = model_cls(data)
        flat = dict(model.flatten())
        data = {'%s:%d:%s' % (name, ob_id, key): flat[key] for key in flat}
        self._r.mset(data)
        return ob_id

    def get(self, name, ob_id):
        model_cls = self.model[name]
        field_names = [c.name for c in model_cls().all_children]
        query = ['%s:%d:%s' % (name, ob_id, key) for key in field_names]
        result = self._r.mget(query)
        data = zip(field_names, result)
        model = PointModel.from_flat(data)
        return model.value
