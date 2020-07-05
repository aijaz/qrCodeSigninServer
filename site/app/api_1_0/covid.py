from flask import request, jsonify, current_app
import datetime
import re
from . import api, get_cursor

from .authentication import auth, unauthorized, key_failure


@api.route('/signins', methods=['GET'])
def current_signins():
    token = request.headers.get('token')
    if token is None or auth(token) is None:
        return unauthorized()
    key = current_app.config.get('DB_KEY')
    if key is None:
        return key_failure()

    less_than = request.args.get('less_than')
    return_count = request.args.get('return_count')

    default_return_count = 100
    if return_count is None:
        return_count = default_return_count
    else:
        try:
            return_count = int(return_count)
            if return_count > default_return_count:
                return_count = default_return_count
        except Exception:
            return_count = default_return_count

    try:
        less_than = int(less_than)
    except Exception:
        less_than = None

    cur = get_cursor()

    if less_than is None:
        cur.execute("""
        SELECT id, extract(epoch from dt) as epoch
        , pgp_sym_decrypt(name, %s) as name
        , pgp_sym_decrypt(phone, %s) as phone
        , pgp_sym_decrypt(email, %s) as email
        from covid_signin_sheet order by id desc limit %s
        """, (key, key, key, return_count))
    else:
        cur.execute(
            """SELECT id, extract(epoch from dt) as epoch
            , pgp_sym_decrypt(name, %s) as name 
            , pgp_sym_decrypt(phone, %s) as phone
            , pgp_sym_decrypt(email, %s) as email
             from covid_signin_sheet where id < %s order by id desc limit %s
            """,
            (key, key, key, less_than, return_count))

    rows = cur.fetchall()
    cur.close()
    return jsonify({"data": rows})


@api.route('/signin', methods=['POST'])
def in_person_scan():
    obj = request.json
    token = request.headers.get('token')
    if token is None or auth(token) is None:
        return unauthorized()
    key = current_app.config.get('DB_KEY')
    if key is None:
        return key_failure()

    name = obj.get("name")
    phone = obj.get("phone")
    email = obj.get("email")
    scan_time = obj.get("scan_time")
    if scan_time is None:
        scan_time = 0

    scan_time = datetime.datetime.fromtimestamp(scan_time)

    name = re.sub("[^a-zA-Z ]", '', name)[:50]
    email = re.sub("[^a-zA-Z0-9_\-+@ .]", '', email)[:50]
    phone = re.sub("[^0-9 ()\-xX]", '', phone)[:18]

    cur = get_cursor()
    cur.execute(
        "SELECT f_covid_signin(%s, %s, %s, %s, %s) as uuid",
        (scan_time, name, phone, email, key))
    cur.fetchone()
    cur.close()
    return jsonify({"result": "1"})
