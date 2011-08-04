import flask

import OsmApi
import yaml

from database import db
from frontend import frontend, oid

def configure_app(app, workdir):
    import os.path
    workdir = os.path.abspath(workdir)

    app.config['OSMPOINT_ADMINS'] = []

    config_file = os.path.join(workdir, 'config.py')
    app.config.from_pyfile(config_file, silent=False)

    points_dump_file = app.config['IMPORTED_POINTS_PATH'] + '/points.yaml'
    try:
        app.config['IMPORTED_POINTS'] = yaml.load(file(points_dump_file, 'r'))
    except IOError:
        app.config['IMPORTED_POINTS'] = []

    with app.test_request_context():
        db.create_all()

def create_app(workdir):
    app = flask.Flask(__name__)
    db.init_app(app)
    oid.init_app(app)

    app.register_blueprint(frontend)

    configure_app(app, workdir)

    return app
