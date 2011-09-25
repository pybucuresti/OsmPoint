import os
from flaskext.actions import Manager
from application import create_app


def maybe_redis_server(app):
    if app.config['REDIS_RUN']:
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
    app = create_app(os.environ['OSMPOINT_WORKDIR'])
    manager = Manager(app, default_server_actions=True)
    with maybe_redis_server(app):
        manager.run()

if __name__ == '__main__':
    main()
