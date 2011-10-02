import logging
import flask
from nose.plugins import Plugin
import frontend


log = logging.getLogger(__name__)


testing_blueprint = flask.Blueprint('testing', __name__)

@testing_blueprint.route('/jstests')
def jstests():
    return flask.render_template('jstests.html')

@testing_blueprint.route('/points.json')
def points_json():
    return flask.jsonify({
        'points': frontend.points_for_homepage(),
    })



redis_sock_path = None

class RedisDb(Plugin):
    """ Run a Redis server child process during tests. """

    name = 'redisdb'

    def begin(self):
        import py.path
        from osmpoint.database import redis_server_process

        self.tmp = py.path.local.mkdtemp()
        log.info("starting up redis in %r", self.tmp)

        sock_path = self.tmp/'redis.sock'
        data_path = self.tmp/'redis.db'

        self.process = redis_server_process(str(sock_path), str(data_path),
                                            persist=False)
        self.process.__enter__()

        global redis_sock_path
        redis_sock_path = sock_path

    def afterTest(self, test):
        import redis
        r = redis.Redis(unix_socket_path=str(redis_sock_path))
        r.flushdb()
        log.info("flushed db")

    def finalize(self, result):
        log.info("stopping redis")

        global redis_sock_path
        redis_sock_path = None

        self.process.__exit__(None, None, None)
        self.tmp.remove()
