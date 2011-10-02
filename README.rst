Installation
============

* Create a Python virtualenv.
* Run ``pip install -r requirements-dev.txt``.
* Run ``pip install -e .`` (current directory being the repository root).
* Create a runtime folder and copy ``example-config.py`` inside, renamed
  to ``config.py``.
* Set a random value to the ``SECRET_KEY`` configuration option.
* Set an environment variable ``OSMPOINT_WORKDIR`` to point to the
  runtime folder created above.
* Run tests with ``nosetests``, or ``nosetests --with-redis`` (which
  starts a single shared Redis process for all the tests)
* Run the server with ``osmpoint runserver``, or ``osmpoint runserver
  --with-redis`` (which starts a Redis server in the background).
