import flask

import OsmApi

from database import db
from frontend import frontend, oid

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


def create_app(workdir):
    app = flask.Flask(__name__)
    db.init_app(app)
    oid.init_app(app)

    app.register_blueprint(frontend)

    configure_app(app, workdir)

    return app
