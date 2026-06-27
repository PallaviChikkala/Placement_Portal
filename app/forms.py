from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo, ValidationError
import re, requests
from flask import current_app

def password_strength_check(form, field):
    pwd = field.data or ''
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-={}\[\]|\\;:\"\',.<>/?]).{8,}$'
    if not re.match(pattern, pwd):
        raise ValidationError('Password must be at least 8 characters long and include uppercase, lowercase, number, and special character.')

class RegistrationForm(FlaskForm):
    email = StringField('University Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), password_strength_check])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    recaptcha = HiddenField('reCAPTCHA')
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    recaptcha = HiddenField('reCAPTCHA')
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class OTPForm(FlaskForm):
    otp = StringField('One‑Time Password', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    recaptcha = HiddenField('reCAPTCHA')
    submit = SubmitField('Send OTP')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), password_strength_check])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

def verify_recaptcha(response_token, remote_ip=None):
    secret = current_app.config.get('RECAPTCHA_SECRET_KEY')
    payload = {'secret': secret, 'response': response_token}
    if remote_ip:
        payload['remoteip'] = remote_ip
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = r.json()
    return result.get('success', False)
