from fabric.api import env, local, cd, run, put, settings, hide
from fabric.contrib.files import exists

from local_fabfile import *

server_name, server_prefix = server.split(':')
server_repo = "%s/src/OsmPoint" % server_prefix
server_virtualenv = "%s/virtualenv" % server_prefix

osmapi_url = ("http://svn.openstreetmap.org/applications/utils/python_lib/"
              "OsmApi/OsmApi.py")


def _push_code():
    local("git push -f '%s:%s' HEAD:incoming" % (server_name, server_repo))

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

    with cd(server_virtualenv):
        run("mkdir -p var")
        if run("test -f var/secret || echo 'missing'"):
            run("OSMPOINT_WORKDIR=var bin/osmpoint "
                "generate_secret_key > var/secret")

def push():
    _push_code()
    with cd(server_repo):
        run("git reset incoming --hard")

def app_start():
    with cd(server_virtualenv):
        run("OSMPOINT_WORKDIR=var "
            "bin/osmpoint runfcgi "
            "--socket var/fcgi.socket "
            "--pidfile var/fcgi.pid "
            "--daemonize")
        run("chmod 777 var/fcgi.socket")

def app_stop():
    with cd(server_virtualenv):
        run("kill `cat var/fcgi.pid` && rm var/fcgi.pid && rm var/fcgi.socket")

def app_restart():
  app_stop()
  app_start()
