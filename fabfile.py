from StringIO import StringIO
from fabric.api import env, local, cd, run, put, settings, hide
from fabric.contrib.files import exists

from local_fabfile import *

server_name, server_prefix = server.split(':')
server_repo = "%s/src/OsmPoint" % server_prefix
server_virtualenv = "%s/virtualenv" % server_prefix
server_var = "%s/var" % server_prefix

osmapi_url = ("http://svn.openstreetmap.org/applications/utils/python_lib/"
              "OsmApi/OsmApi.py")

PRODUCTION_CONFIG = """\
import os
import logging
import yaml

workdir = os.path.dirname(__file__)

OPENID_FS_STORE_PATH = os.path.join(workdir, 'openid_store')
OSM_PASSWORD_PATH = os.path.join(workdir,'osm-login.txt')
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(workdir, 'db.sqlite3')

with open(os.path.join(workdir, 'secret'), 'rb') as f:
    SECRET_KEY = f.read().strip()

# Choose API:
#OSM_API = "www.openstreetmap.org" #main api
OSM_API = "api06.dev.openstreetmap.org" #development

IMPORTED_POINTS_PATH = os.path.join(workdir, 'points.yaml')

OSMPOINT_ADMINS = [
    # Alex Morega:
    'http://grep.ro/openid',
    ('https://www.google.com/accounts/o8/id?'
     'id=AItOawlvc4WaevDOhwzbc2j3rM74GSF9Cy5gMbY'),
    # Groza Camelia:
    'http://camelia-groza.myopenid.com/',
    ('https://www.google.com/accounts/o8/id?'
     'id=AItOawkmpwuvvH5diF-QG_ExmxGV6Cj-0vdEIKQ'),
]

CLOUDMADE_API_KEY = "87d74b5d089842f98679496ee6aef22e"

logging.basicConfig(filename=os.path.join(workdir, 'osmpoint.log'),
                    level=logging.INFO)
logging.getLogger('osmpoint').setLevel(logging.INFO)
data_log_handler = logging.FileHandler(os.path.join(workdir, 'data.log'))
logging.getLogger('osmpoint.database').addHandler(data_log_handler)
"""


def _push_code():
    local("git push -f '%s:%s' HEAD:incoming" % (server_name, server_repo))

def configure():
    run("mkdir -p '%s'" % server_var)
    with cd(server_var):
        if run("test -f secret || echo 'missing'"):
            run("OSMPOINT_WORKDIR=. ../virtualenv/bin/osmpoint "
                "generate_secret_key > secret")
        put(StringIO(PRODUCTION_CONFIG), "config.py")

def install_server():
    run("mkdir -p '%s'" % server_prefix)
    run("mkdir -p '%s/www'" % server_prefix)

    if not exists(server_repo):
        run("mkdir -p '%s'" % server_repo)
        with cd(server_repo):
            run("git init")
        _push_code()
        with cd(server_repo):
            run("git checkout incoming -b deploy")

    _push_code()

    if not exists(server_virtualenv):
        run("virtualenv -p /usr/bin/python --distribute '%s'" %
            server_virtualenv)

    with cd(server_virtualenv):
        run("bin/pip install -e '%s'" % server_repo)
        run("bin/pip install flup")
        site_packages = run("ls -d lib/python*/site-packages")

    with cd(server_virtualenv + '/' + site_packages):
        osmapi_filename = osmapi_url.rsplit('/', 1)[-1]
        if run("test -f '%s' || echo 'missing'" % osmapi_filename):
            run("curl -O '%s'" % osmapi_url)

    configure()

def push():
    _push_code()
    with cd(server_repo):
        run("git reset incoming --hard")
    with cd(server_virtualenv):
        run("bin/pip install -e '%s'" % server_repo)

def start():
    with cd(server_var):
        run("OSMPOINT_WORKDIR=. "
            "../virtualenv/bin/osmpoint runfcgi "
            "--socket fcgi.socket "
            "--pidfile fcgi.pid "
            "--daemonize")
        run("chmod 777 fcgi.socket")

def stop():
    with cd(server_var):
        run("kill `cat fcgi.pid` && rm fcgi.pid && rm fcgi.socket")

def restart():
    try:
        stop()
    except:
        pass

    start()

def deploy():
    push()
    configure()
    restart()
