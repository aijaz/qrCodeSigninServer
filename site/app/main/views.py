from flask import redirect, render_template, current_app, send_file, flash
from . import get_cursor
import re
import subprocess
import io
import random

from . import main
from .forms import CovidContactForm, EventReservationForm
# from reportlab.lib.pagesizes import letter, A4
# from reportlab.pdfgen import canvas
# from reportlab.platypus import Image
#

@main.route('/eid', methods=['POST', 'GET'])
def eid_reservation():
    key = current_app.config.get('DB_KEY')
    if key is None:
        return "The system is starting up. Please wait a few minutes and try again."

    cur = get_cursor()
    cur.execute("select * from f_available_slots_report()")
    slots = cur.fetchall()

    form = EventReservationForm()
    if form.validate_on_submit():
        return_hash = handle_eid_form(form, cur, key)
        result = return_hash["result"]
        if result == 'too_many_slots_requested':
            flash("Too many slots requested. Please try again")
        elif result == 'not_enough_slots_available':
            flash("Not enough slots available. Please try again")
        elif result == 'success':
            cur.close()
            return handle_successful_reservation(return_hash, slots)
        else:
            flash("There was an error processing your request. Please try again")

    cur.close()
    return render_template("eventForm.html", form=form, slots=slots)


def handle_successful_reservation(hash, slots):
    working_dir = current_app.config["QRCODE_WORKING_DIR"]
    path_to_execs = current_app.config["BIN_DIR"]

    convert_path = path_to_execs + "/convert"
    composite_path = path_to_execs + "/composite"

    the_uuid = hash["reservation_id"]
    num_m = hash["num_m"]
    num_f = hash["num_f"]
    uuid_str = "/tmp/" + the_uuid
    qrcode_file = uuid_str + ".png"
    qrcode_file_resized = uuid_str + ".resized.png"
    qrcode_file_grown = uuid_str + ".grown.png"
    qrcode_file_composite = uuid_str + ".composite.png"
    qrcode_file_name = uuid_str + ".name.png"
    qrcode_file_final = uuid_str + ".final.png"
    qrcode_file_warn = uuid_str + ".warn.png"
    api_version = "3"
    num = hash["num_m"]
    if hash["morf"] == "F":
        num = hash["num_f"]
    qrcode_string = "+".join([api_version, the_uuid, hash["name"], hash["phone"], hash["email"], hash["morf"], "{0}".format(num)])
    redirect_url = "/eventImage/{0}".format(the_uuid)

    hash["event_name"] = ""
    for slot in slots:
        if slot["event_id"] == hash["event_id"]:
            hash["event_name"] = slot["event_name"]
            break


    first_y = 750
    delta_y = 17

    name_x = 90
    name_y = 620

    name_width = 700 - (name_x * 2)
    name_height = 120

    with open(qrcode_file, "w") as file:
        subprocess.run(["qr", qrcode_string], stdout=file)
        subprocess.run([convert_path, qrcode_file, '-resize', "700x700", qrcode_file_resized])
        subprocess.run(
            [convert_path, qrcode_file_resized, '-resize', "700x920", '-extent', "700x920", qrcode_file_grown])
        # subprocess.run([composite_path
        #                    , '-geometry', '+550+800'
        #                    , '{0}/logo.png'.format(working_dir)
        #                    , qrcode_file_grown
        #                    , qrcode_file_composite])

        # create name image
        subprocess.run([convert_path,
                        '-font',
                        working_dir + "/MontserratBlack-ZVK6J.otf",
                        '-size',
                        '{0}x{1}'.format(name_width, name_height),
                        """caption:{0}""".format(hash["event_name"]),
                        qrcode_file_name])
        subprocess.run([composite_path, '-geometry', '+{0}+{1}'.format(name_x, name_y), qrcode_file_name,
                        qrcode_file_grown, qrcode_file_composite])

        people_string = ""
        if num_f == 0:
            people_string = "{0} brother{1}".format(num_m, "s" if num_m != 1 else "")
        else:
            people_string = "{0} sister{1}".format(num_f, "s" if num_f != 1 else "")

        subprocess.run([convert_path,
                        '-font',
                        working_dir + "/MontserratBlack-ZVK6J.otf",
                        '-size',
                        '{0}x{1}'.format(name_width, name_height),
                        """caption:{0}""".format(people_string),
                        qrcode_file_name])
        subprocess.run([composite_path, '-geometry', '+{0}+{1}'.format(name_x, name_y+100), qrcode_file_name,
                        qrcode_file_composite, qrcode_file_composite])

        subprocess.run([convert_path,
                        '-font',
                        working_dir + "/MontserratLight-6YemM.otf",
                        '-size',
                        '{0}x{1}'.format(name_width, 100),
                        """caption:{0} {1}""".format(
                            "This is your personal receipt. " +
                            "Please save it or print it, and do not share it with anyone. " +
                            "Present it to Security when you visit the building. Ticket #: ", the_uuid),
                        qrcode_file_warn])

        subprocess.run(
            [composite_path, '-geometry', '+{0}+{1}'.format(name_x, first_y + (3 * delta_y)), qrcode_file_warn,
             qrcode_file_composite, qrcode_file_composite])



        subprocess.run([convert_path,
                        '-font',
                        working_dir + "/MontserratLight-6YemM.otf",
                        '-size',
                        '{0}x{1}'.format(name_width, 42),
                        """caption:{0}""".format(
                            "Masjid Ikhlas Eid Prayers. July 31, 2020"),
                        qrcode_file_warn])

        subprocess.run(
            [composite_path, '-geometry', '+{0}+{1}'.format(name_x, 44), qrcode_file_warn,
             qrcode_file_composite, qrcode_file_composite])


        subprocess.run([composite_path
                           , '-geometry', '+10+10'
                           , '{0}/logo.png'.format(working_dir)
                           , qrcode_file_composite
                           , qrcode_file_final])






    subprocess.run(
        ["/bin/rm", qrcode_file, qrcode_file_resized, qrcode_file_grown, qrcode_file_composite, qrcode_file_name,
         qrcode_file_warn])
    return redirect(redirect_url)

def handle_eid_form(form, cur, key):
    values = clean_form_input(form)

    cur.execute("select * from f_reserve_slots(%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    values["event_id"]
                    , values["num_m"]
                    , values["num_f"]
                    , values["name"]
                    , values["phone"]
                    , values["email"]
                    , key
                    , 6
                ))
    reservation_result = cur.fetchone()
    return_hash = {**reservation_result, **values}
    return return_hash




def clean_form_input(form):
    values = {}
    dirty_name = form.name.data
    values["name"] = re.sub("[^a-zA-Z ]", '', dirty_name)[:50]

    dirty_email = form.email.data
    values["email"] = re.sub("[^a-zA-Z0-9_\-+@ .]", '', dirty_email)[:50]

    dirty_phone = form.phone_number.data
    values["phone"] = re.sub("[^0-9 ()\-xX]", '', dirty_phone)[:18]

    try:
        values["event_id"] = int(form.event_id.data)
    except ValueError:
        values["event_id"] = 0

    if form.for_whom.data == 'f':
        values["morf"] = "F"
        try:
            values["num_f"] = int(form.num.data)
        except ValueError:
            values["num_f"] = 0
        values ["num_m"] = 0
    else:
        values["morf"] = "M"
        try:
            values["num_m"] = int(form.num.data)
        except ValueError:
            values["num_m"] = 0
        values["num_f"] = 0


    return values


@main.route('/', methods=['POST', 'GET'])
def contact_trace():
    key = current_app.config.get('DB_KEY')
    if key is None:
        return "The system is starting up. Please wait a few minutes and try again."

    form = CovidContactForm()
    if form.validate_on_submit():
        api_version = '2'

        dirty_name = form.name.data
        name = re.sub("[^a-zA-Z ]", '', dirty_name)[:50]

        dirty_email = form.email.data
        email = re.sub("[^a-zA-Z0-9_\-+@ .]", '', dirty_email)[:50]

        dirty_phone = form.phone_number.data
        phone = re.sub("[^0-9 ()\-xX]", '', dirty_phone)[:18]

        the_uuid = get_id()

        qrcode_string = "+".join([api_version, name, phone, email])

        cur = get_cursor()
        cur.execute("""
        INSERT INTO covid_qrcodes(name, phone, email) values(
        pgp_sym_encrypt(%s, %s)
        , pgp_sym_encrypt(%s, %s)
        , pgp_sym_encrypt(%s, %s))
        """, (name, key, phone, key, email, key))
        cur.close()

        working_dir = current_app.config["QRCODE_WORKING_DIR"]
        path_to_execs = current_app.config["BIN_DIR"]

        convert_path = path_to_execs + "/convert"
        composite_path = path_to_execs + "/composite"

        uuid_str = "/tmp/" + the_uuid
        qrcode_file = uuid_str + ".png"
        qrcode_file_resized = uuid_str + ".resized.png"
        qrcode_file_grown = uuid_str + ".grown.png"
        qrcode_file_composite = uuid_str + ".composite.png"
        qrcode_file_name = uuid_str + ".name.png"
        qrcode_file_final = uuid_str + ".final.png"
        qrcode_file_warn = uuid_str + ".warn.png"
        redirect_url = "/covidImage/{0}".format(the_uuid)

        first_y = 450
        delta_y = 17

        name_x = 40
        name_y = 350

        name_width = 370 - (name_x * 2)
        name_height = 80

        with open(qrcode_file, "w") as file:
            subprocess.run(["qr", qrcode_string], stdout=file)
            subprocess.run([convert_path, qrcode_file, '-resize', "370x370", qrcode_file_resized])
            subprocess.run(
                [convert_path, qrcode_file_resized, '-resize', "370x580", '-extent', "370x580", qrcode_file_grown])
            subprocess.run([composite_path
                               , '-geometry', '+270+430'
                               , '{0}/logo.png'.format(working_dir)
                               , qrcode_file_grown
                               , qrcode_file_composite])

            # create name image
            subprocess.run([convert_path,
                            '-font',
                            working_dir + "/MontserratBlack-ZVK6J.otf",
                            '-size',
                            '{0}x{1}'.format(name_width, name_height),
                            """caption:{0}""".format(name),
                            qrcode_file_name])
            subprocess.run([composite_path, '-geometry', '+{0}+{1}'.format(name_x, name_y), qrcode_file_name,
                            qrcode_file_composite, qrcode_file_composite])

            subprocess.run([convert_path,
                            '-font',
                            working_dir + "/MontserratLight-6YemM.otf",
                            '-size',
                            '{0}x{1}'.format(name_width, 60),
                            """caption:{0}""".format(
                                "This is your personal QR Code. "+
                                "Please save it, and do not share it with anyone. "+
                                "Present it to Security when you visit the building."),
                            qrcode_file_warn])
            subprocess.run(
                [composite_path, '-geometry', '+{0}+{1}'.format(name_x, first_y + (3 * delta_y)), qrcode_file_warn,
                 qrcode_file_composite, qrcode_file_composite])

            subprocess.run([convert_path,
                            qrcode_file_composite,
                            '-font',
                            working_dir + "/MontserratBold-p781R.otf",
                            '-draw',
                            """text 40, {1} '{0}'""".format(phone, first_y),
                            '-draw',
                            """text 40, {1} '{0}'""".format(email, first_y + delta_y),
                            qrcode_file_final])

        subprocess.run(
            ["/bin/rm", qrcode_file, qrcode_file_resized, qrcode_file_grown, qrcode_file_composite, qrcode_file_name,
             qrcode_file_warn])
        return redirect(redirect_url)

    return render_template("covidForm.html", form=form)


@main.route('/covidImage/<the_uuid>', methods=['GET'])
def covid_image(the_uuid):
    uuid_str = "/tmp/" + the_uuid
    qrcode_file_final = uuid_str + ".final.png"
    response_file = the_uuid + ".png"

    with open(qrcode_file_final, 'rb') as image:
        return send_file(
            io.BytesIO(image.read()),
            attachment_filename=response_file,
            mimetype='image/png'
        )

@main.route('/eventImage/<the_uuid>', methods=['GET'])
def event_image(the_uuid):
    uuid_str = "/tmp/" + the_uuid
    qrcode_file_final = uuid_str + ".final.png"
    response_file = the_uuid + ".png"

    with open(qrcode_file_final, 'rb') as image:
        return send_file(
            io.BytesIO(image.read()),
            attachment_filename=response_file,
            mimetype='image/png'
        )

@main.route('/eventPDF/<the_uuid>', methods=['GET'])
def event_pdf(the_uuid):
    uuid_str = "/tmp/" + the_uuid
    qrcode_file_final = uuid_str + ".pdf"
    response_file = the_uuid + ".pdf"

    with open(qrcode_file_final, 'rb') as image:
        return send_file(
            io.BytesIO(image.read()),
            attachment_filename=response_file,
            mimetype='application/pdf'
        )


def get_id():
    characters = '0123456789BCDFGHJKLMNPQRSTVWXYZbcdfghjklmnpqrstvwxyz-_'
    result = ''
    for i in range(0, 10):
        result += random.choice(characters)

    return result
