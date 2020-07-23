from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class CovidContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    phone_number = StringField("Your Phone Number", validators=[DataRequired()])
    email = StringField("Your email address")


class EventReservationForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    phone_number = StringField("Your Phone Number", validators=[DataRequired()])
    email = StringField("Your email address")
    num = StringField("Number of people attending", validators=[DataRequired()])
    for_whom = StringField("Brothers or Sister", validators=[DataRequired()])
    event_id = StringField("Event ID", validators=[DataRequired()])
