from config import config
from flask import Flask, current_app, g
from psycopg2.pool import ThreadedConnectionPool
from flask_bootstrap import Bootstrap
import os

bootstrap = Bootstrap()


def create_app(config_name):
    app = Flask(__name__)
    current_config = config[config_name]
    app.config.from_object(current_config)
    current_config.init_app(app)

    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
    bootstrap.init_app(app)

    # attach routes and error pages here
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')

    @app.before_request
    def before_request():
        g.conn = current_app.connection_pool.getconn()

    @app.teardown_request
    def teardown(exc):
        g.conn.commit()
        current_app.connection_pool.putconn(g.conn)

    min_connections = 5
    max_connections = 10
    app.connection_pool = ThreadedConnectionPool(min_connections
                                                 , max_connections
                                                 , host=app.config["DB_HOST_NAME"]
                                                 , database=app.config["DB_DB_NAME"]
                                                 , user=app.config["DB_USER_NAME"])

    return app
