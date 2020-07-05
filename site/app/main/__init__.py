from flask import Blueprint, g
import psycopg2.extras

main = Blueprint('main', __name__)


def get_cursor():
    return g.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

from . import views
