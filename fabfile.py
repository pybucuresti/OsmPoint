from fabric.api import env, local, cd, run, put, settings, hide
from fabric.contrib.files import exists

from local_fabfile import *

server_name, server_prefix = server.split(':')
server_repo = "%s/src/OsmPoint" % server_prefix
server_virtualenv = "%s/virtualenv" % server_prefix


def _push_code():
    local("git push -f '%s:%s' HEAD:incoming" % (server_name, server_repo))

def install_server():
    run("mkdir -p '%s'" % server_prefix)

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

def push():
    _push_code()
    with cd(server_repo):
        run("git reset incoming --hard")
