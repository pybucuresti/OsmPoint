import os
from flaskext.actions import Manager
from osm_point import create_app

def main():
    app = create_app(os.environ['OSMPOINT_WORKDIR'])
    manager = Manager(app, default_server_actions=True)
    manager.run()

if __name__ == '__main__':
    main()
