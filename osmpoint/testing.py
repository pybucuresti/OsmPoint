import logging
import flask
from nose.plugins import Plugin
import py.path
import frontend

__test__ = [] # tell nose to skip this module

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

@testing_blueprint.route('/reset_database', methods=['POST'])
def reset_database():
    rdb = flask.current_app.rdb
    rdb.r.flushdb()
    return "ok"

@testing_blueprint.route('/log_in_as', methods=['POST'])
def log_in_as():
    # log in with any user ID, for testing purposes
    flask.session['openid'] = flask.request.form['user_id']
    return "ok"



def redis_for_testing(tmp, addCleanup):
    from osmpoint.testing import redis_sock_path
    if redis_sock_path is not None:
        return redis_sock_path

    from osmpoint.database import redis_server_process
    sock_path = tmp/'redis.sock'
    data_path = tmp/'redis.db'
    p = redis_server_process(str(sock_path), str(data_path), persist=False)
    p.__enter__()
    addCleanup(lambda: p.__exit__(None, None, None))
    return sock_path


def app_for_testing(addCleanup):
    from application import create_app

    tmp_dir = py.path.local.mkdtemp()
    redis_socket_path = redis_for_testing(tmp_dir, addCleanup)
    config_for_tests = ("OSM_API = 'api06.dev.openstreetmap.org'\n"
                        "SECRET_KEY = 'my-secret-key'\n"
                        "SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/db.sqlite'\n"
                        "MAIL_SERVER = 'my_mailhost'\n"
                        "MAIL_FROM = 'server@example.com'\n"
                        "MAIL_ADMIN = 'me@example.com'\n"
                        "IMPORTED_POINTS_PATH = '.'\n"
                        "REDIS_SOCKET_PATH = '%s'\n"
                       ) % (tmp_dir, redis_socket_path)
    tmp_dir.join('config.py').write(config_for_tests)
    addCleanup(tmp_dir.remove)

    app = create_app(str(tmp_dir))
    app.register_blueprint(testing_blueprint)

    app.try_trigger_before_first_request_functions()
    return app


redis_sock_path = None

class RedisDb(Plugin):
    """ Run a Redis server child process during tests. """

    name = 'redisdb'

    def begin(self):
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
