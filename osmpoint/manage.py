import sys
import os
from flaskext.actions import Manager
from application import create_app


def migrate_to_redis_cmd(app):
    def cmd():
        import database
        app.try_trigger_before_first_request_functions()
        with app.test_request_context():
            database.migrate_to_redis()
    return cmd


def maybe_redis_server(app, redis_requested):
    if redis_requested and 'WERKZEUG_RUN_MAIN' not in os.environ:
        from database import redis_server_process
        return redis_server_process(app.config['REDIS_SOCKET_PATH'],
                                    app.config['REDIS_DATA_PATH'])
    else:
        from contextlib import contextmanager
        @contextmanager
        def dummy():
            yield
        return dummy()


def main():
    if '--with-redis' in sys.argv:
        redis_requested = True
        sys.argv.remove('--with-redis')
    else:
        redis_requested = False

    app = create_app(os.environ['OSMPOINT_WORKDIR'])
    manager = Manager(app, default_server_actions=True)
    manager.add_action('migrate_to_redis', migrate_to_redis_cmd)

    with maybe_redis_server(app, redis_requested):
        manager.run()

if __name__ == '__main__':
    main()
