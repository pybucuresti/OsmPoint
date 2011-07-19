import os
import logging

workdir = os.path.dirname(__file__)

OPENID_FS_STORE_PATH = os.path.join(workdir, 'openid_store')
OSM_PASSWORD_PATH = os.path.join(workdir,'osm-login.txt')
SQLALCHEMY_DATABASE_URI = "sqlite:///%s" % os.path.join(workdir, 'db.sqlite3')

#SECRET_KEY = "replace-with-a-random-string"

DEBUG = True
STATIC_CACHE_TIMEOUT = 0
OSMPOINT_ADMINS = []

logging.basicConfig()
