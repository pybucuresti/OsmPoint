from flaskext.sqlalchemy import SQLAlchemy


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

def del_point(point):
    db.session.delete(point)
    db.session.commit()

def get_osm_api():
    osm_password_path = flask.current_app.config['OSM_PASSWORD_PATH']
    return OsmApi.OsmApi(passwordfile=osm_password_path)

def submit_points_to_osm(point_to_submit):
    osm = get_osm_api()
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
