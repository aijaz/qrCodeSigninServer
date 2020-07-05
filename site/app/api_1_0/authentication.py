from flask import request, jsonify
from . import api, get_cursor


@api.route('/login', methods=['POST'])
def login():
    obj = request.json
    email = obj.get('email')
    password = obj.get('password')
    source = obj.get('source')
    cur = get_cursor()
    cur.execute("select * from f_login(%s, %s, %s)", (email, password, source))
    row = cur.fetchone()
    cur.close()
    if row is None:
        return unauthorized()
    return jsonify(row)


@api.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('token')
    if token is None or auth(token) is None:
        return unauthorized()
    cur = get_cursor()
    cur.execute("select * from f_logout(%s)", (token,))
    cur.close()


def user_id():
    token = request.headers.get('token')
    if token is None:
        return None
    auth_req = auth(token)
    if auth_req is None:
        return None
    return auth_req.get('id')


@api.route('/verifyPasswordChange', methods=['POST'])
def verify_password_change():
    obj = request.json
    password = obj.get('password')
    guid = obj.get('guid')

    cur = get_cursor()

    cur.execute("SELECT * FROM f_change_password_forgot(%s, %s)", (guid, password))
    row = cur.fetchone()
    if row is None:
        return unauthorized()
    cur.close()

    return jsonify("")


@api.route('/changePassword', methods=['POST'])
def change_password():
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    obj = request.json
    old_password = obj.get('old_password')
    new_password = obj.get('password')

    cur = get_cursor()
    cur.execute("SELECT * FROM f_change_password(%s, %s, %s)", (my_user_id, old_password, new_password))
    row = cur.fetchone()
    cur.close()
    if row is None:
        return unauthorized()

    return jsonify("")


def is_admin(my_user_id, cur):
    cur.execute("SELECT admin from team_member where id=%s", (my_user_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return row["admin"]


@api.route('/requestPasswordReset', methods=['POST'])
def request_password_reset():
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    cur = get_cursor()
    if not is_admin(my_user_id, cur):
        return unauthorized()

    obj = request.json
    email = obj.get('email')

    cur.execute("SELECT * FROM f_forgot(%s)", (email,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        return unauthorized()

    return jsonify(row)


@api.route('/user', methods=['POST'])
def add_user():
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    cur = get_cursor()
    if not is_admin(my_user_id, cur):
        return unauthorized()

    obj = request.json
    email = obj.get('email')
    admin = obj.get('admin')
    name = obj.get('name')
    read_only = obj.get('read_only')

    if email is None or admin is None or name is None or read_only is None:
        return bad_request()

    cur.execute("SELECT * FROM f_add_team_member(%s, %s, %s, %s)", (email, admin, name, read_only))
    row = cur.fetchone()
    cur.close()

    return jsonify(row)


@api.route('/user/<int:p_id>', methods=['DELETE'])
def delete_user(p_id):
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    cur = get_cursor()
    if not is_admin(my_user_id, cur):
        return unauthorized()

    cur.execute("update team_member set password = %s where id = %s", ('', p_id))
    cur.execute("delete from forgot_message where id = %s", (p_id,))
    cur.close()

    return jsonify("")


@api.route('/user/<int:requested_user_id>', methods=['GET'])
def get_user(requested_user_id):
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    cur = get_cursor()
    if not is_admin(my_user_id, cur):
        return unauthorized()

    cur.execute("SELECT id, name, email, admin, read_only FROM team_member where id = %s", (requested_user_id,))
    row = cur.fetchone()
    cur.close()

    return jsonify(row)


@api.route('/users', methods=['GET'])
def list_users():
    my_user_id = user_id()
    if my_user_id is None:
        return unauthorized()

    cur = get_cursor()
    if not is_admin(my_user_id, cur):
        return unauthorized()

    cur.execute("SELECT id, name, email, admin, read_only FROM team_member order by id")
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)


def auth(token):
    cur = get_cursor()
    cur.execute("select * from f_auth(%s)", (token,))
    row = cur.fetchone()
    cur.close()
    return row


def unauthorized():
    response = jsonify({'message': 'Login Failed'})
    return response, 401


def key_failure():
    response = jsonify({'message': 'Key Failure'})
    return response, 503


def bad_request():
    response = jsonify("")
    return response, 400
