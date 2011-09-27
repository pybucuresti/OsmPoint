import logging
from contextlib import contextmanager
from flaskext.sqlalchemy import SQLAlchemy
import flask
import OsmApi
import flatland as fl

log = logging.getLogger(__name__)
rlog = logging.getLogger(__name__ + '.redis')
osmlog = logging.getLogger(__name__ + '.osm')
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
    rdb = flask.current_app.rdb
    return rdb.put_object('point', None, {
        'lat': latitude,
        'lon': longitude,
        'name': name,
        'url': url,
        'amenity': amenity,
        'user_open_id': user_open_id,
    })
    return point.id

def get_all_points():
    rdb = flask.current_app.rdb
    for p_id in rdb.object_ids('point'):
        yield p_id, rdb.get_object('point', int(p_id))

def migrate_to_redis():
    rlog.info("Flushing database and loading points from SQL")
    rdb = flask.current_app.rdb
    rdb.r.flushdb()
    last_id = 0
    count = 0
    for p in Point.query.all():
        rdb.put_object('point', p.id, {
            'lat': p.latitude,
            'lon': p.longitude,
            'name': p.name,
            'url': p.url,
            'amenity': p.amenity,
            'osm_id': p.osm_id,
            'user_open_id': p.user_open_id,
        })
        last_id = max([last_id, p.id])
        count += 1
    rdb.r.set('point:last_id', last_id)
    rlog.info("Finished importing %d points, last_id is %d", count, last_id)

def set_point_field(p_id, key, value):
    # TODO move to RedisDb class
    rlog.info("SET point:%d:%s = %r", p_id, key, value)
    rdb = flask.current_app.rdb
    rdb.r.set('point:%d:%s' % (p_id, key), value)

def del_point(p_id):
    rdb = flask.current_app.rdb
    rdb.del_object('point', p_id)

def get_point_or_404(p_id):
    rdb = flask.current_app.rdb
    if not rdb.r.sismember('point:ids', p_id):
        flask.abort(404)
    return rdb.get_object('point', p_id)

def get_osm_api():
    app = flask.current_app
    return OsmApi.OsmApi(api=app.config['OSM_API'],
                         passwordfile=app.config['OSM_PASSWORD_PATH'])

def submit_points_to_osm(point_id_list):
    osm = get_osm_api()
    osm._api = flask.current_app.config['OSM_API']
    changeset_id = osm.ChangesetCreate({u"comment": u"Submitted by OsmPoint"})
    osmlog.info("Begin OSM changeset %d", changeset_id)

    rdb = flask.current_app.rdb
    for p_id in point_id_list:
        p = rdb.get_object('point', p_id)
        tags = {
            'name': p['name'],
            'amenity': p['amenity'],
            'source': "poi.grep.ro",
        }
        if p['url']:
            tags['website'] = p['url']

        node_dict = osm.NodeCreate({
            u"lon": p['lon'],
            u"lat": p['lat'],
            u"tag": tags,
        })

        set_point_field(p_id, 'osm_id', node_dict['id'])
        osmlog.info("OSM point: %r", node_dict)

    osm.ChangesetClose()
    osmlog.info("OSM changeset committed")


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
    name = fl.String
    url = fl.String
    amenity = fl.String
    user_open_id = fl.String
    osm_id = fl.Integer


class RedisDb(object):

    def __init__(self, r, model_map):
        self.r = r
        self.model = model_map

    def put_object(self, name, ob_id, data):
        if ob_id is None:
            ob_id = self.r.incr('%s:last_id' % name)
        rlog.info("SET %s:%d:* = %r", name, ob_id, data)
        try:
            model_cls = self.model[name]
            model = model_cls(data)
            flat = dict(model.flatten())
            data = {'%s:%d:%s' % (name, ob_id, key): flat[key]
                    for key in flat if not model[key].is_empty}
            self.r.mset(data)
            self.r.sadd('%s:ids' % name, ob_id)
            return ob_id
        except:
            rlog.error("failed during SET %s:%d:*", name, ob_id)
            raise

    def get_object(self, name, ob_id):
        model_cls = self.model[name]
        field_names = [c.name for c in model_cls().all_children]
        query = ['%s:%d:%s' % (name, ob_id, key) for key in field_names]
        result = self.r.mget(query)
        decode = lambda v: None if v is None else v.decode('utf-8')
        data = zip(field_names, (decode(v) for v in result))
        model = PointModel.from_flat(data)
        return model.value

    def del_object(self, name, ob_id):
        # TODO delete should be atomic
        rlog.info("DEL %s:%d:*", name, ob_id)
        model_cls = self.model[name]
        field_names = [c.name for c in model_cls().all_children]
        query = ['%s:%d:%s' % (name, ob_id, key) for key in field_names]
        self.r.srem('%s:ids' % name, ob_id)
        self.r.delete(*query)

    def object_ids(self, name):
        return set(int(ob_id) for ob_id in self.r.smembers('%s:ids' % name))


def open_redis_db(sock_path, model_map={'point': PointModel}):
    from redis import Redis
    r = Redis(unix_socket_path=sock_path)
    return RedisDb(r, model_map)

redis_config_tmpl = """\
port 0
unixsocket ${sock_path}
dir ${data_path}
logfile /dev/null
"""
redis_config_persist = """\
appendonly yes
appendfsync always
"""

@contextmanager
def redis_server_process(sock_path, data_path, persist=True):
    import os.path
    import time
    import subprocess
    from string import Template
    rslog = logging.getLogger(__name__ + '.redis-server')

    if not os.path.isdir(data_path):
        os.makedirs(data_path)

    p = subprocess.Popen(['redis-server', '-'], stdin=subprocess.PIPE)

    try:
        p.stdin.write(Template(redis_config_tmpl).substitute(
            sock_path=sock_path,
            data_path=data_path,
        ))
        if persist:
            p.stdin.write(redis_config_persist)
        p.stdin.close()
        rslog.info("started redis with pid %d", p.pid)

        for c in xrange(500):
            if os.path.exists(sock_path):
                break
            time.sleep(.01)
        else:
            raise RuntimeError("Redis socket did not show up")

        yield

    finally:
        rslog.info("asking redis to shut down")
        p.terminate()
        p.wait()
        rslog.info("redis has stopped with exit code %d", p.returncode)
