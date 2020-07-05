import json
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # These are some variables you may want to customize
    DB_DB_NAME = "signindb"
    DB_USER_NAME = "signin"
    DB_HOST_NAME = "localhost"
    PASSWORD_FILE = os.path.join(basedir, 'passwords.json')
    passwords = json.loads(open(PASSWORD_FILE).read())
    SECRET_KEY = passwords["secret_key"]
    DB_KEY = passwords["db_key"]
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    BIN_DIR = "/usr/bin"
    QRCODE_WORKING_DIR = os.path.join(basedir, 'qrcode')
    template_folder = "app/templates"
    static_folder = "app/static"

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    BIN_DIR = "/usr/local/bin"


class TestingConfig(Config):
    TESTING = True


class ProductionConfig(Config):
    BIN_DIR = "/usr/bin"


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': ProductionConfig
}
