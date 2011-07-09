import os
workdir = os.path.abspath(os.environ['OSMPOINT_WORKDIR'])

OPENID_FS_STORE_PATH = os.path.join(workdir, 'openid_store')
OSM_PASSWORD_PATH = os.path.join(workdir,'osm-login.txt')
SQLALCHEMY_DATABASE_URI = "sqlite:///%s" % os.path.join(workdir, 'db.sqlite3')

try:
    with open(os.path.join(workdir, 'secret'), 'rb') as f:
        SECRET_KEY = f.read()
except IOError:
    SECRET_KEY = None # TODO issue a warning in the log

DEBUG = True
STATIC_CACHE_TIMEOUT = 0
OSMPOINT_ADMINS = []

