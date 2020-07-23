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

    num_people = obj.get("num_people")
    morf = obj.get("morf")

    if num_people is None:
        num_people = 1

    if morf != 'F':
        morf = 'M'

    cur = get_cursor()

    for f in range(num_people):
        cur.execute(
            "SELECT f_covid_signin(%s, %s, %s, %s, %s, %s) as uuid",
            (scan_time, name, phone, email, key, morf))
        cur.fetchone()


    cur.close()
    return jsonify({"result": "1"})


@api.route('/signin/<int:p_id>', methods=['GET'])
def get_signin(p_id):
    token = request.headers.get('token')
    if token is None or auth(token) is None:
        return unauthorized()
    key = current_app.config.get('DB_KEY')
    if key is None:
        return key_failure()

    cur = get_cursor()
    cur.execute(
        """SELECT id, extract(epoch from dt) as epoch
            , pgp_sym_decrypt(name, %s) as name 
            , pgp_sym_decrypt(phone, %s) as phone
            , pgp_sym_decrypt(email, %s) as email
             FROM covid_signin_sheet where id = %s""",
        (p_id,))
    row = cur.fetchone()
    cur.close()
    return jsonify(row)


@api.route('/signin/<int:p_id>', methods=['DELETE'])
def delete_signin(p_id):
    token = request.headers.get('token')
    if token is None or auth(token) is None:
        return unauthorized()
    key = current_app.config.get('DB_KEY')
    if key is None:
        return key_failure()

    cur = get_cursor()
    cur.execute(
        "DELETE FROM covid_signin_sheet where id = %s",
        (p_id,))
    cur.execute()
    cur.close()
    return jsonify({})


@api.route('/signin/<int:p_id>', methods=['PUT'])
def put_signin(p_id):
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
        "SELECT f_covid_signin_update (%s, %s, %s, %s, %s) as uuid",
        (p_id, name, phone, email, key))
    cur.fetchone()
    cur.close()
    return jsonify({"result": "1"})


@api.route('/redeemReservation', methods = ['POST'])
def redeem_reservation():
    obj = request.json
    token = request.headers.get('token')
    if token == None or auth(token) == None :
        return unauthorized()
    key = current_app.config.get('DB_KEY')
    if key == None :
        return key_failure()


    the_uuid = obj.get("uuid")
    if the_uuid is None:
        return bad_request()

    morf = obj.get("morf")
    if morf != 'F':
        morf = 'M'

    cur = get_cursor()

    cur.execute("SELECT * FROM f_redeem_reservation(%s, %s, %s)", (the_uuid, morf, key))
    row = cur.fetchone()

    cur.close()
    return jsonify(row)


def bad_request():
    response = jsonify({'message':'Bad Request'})
    return response, 400

