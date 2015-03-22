import os
import sys
from datetime import datetime

from flask import Flask, url_for, redirect, render_template, request, json, jsonify
from flask.ext import admin, login
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from wtforms import form, fields, validators, TextField, TextAreaField, SelectField
from flask.ext.admin.contrib import sqla
from flask.ext.admin import helpers, expose
from flask.ext.mail import Mail, Message

from werkzeug.security import generate_password_hash, check_password_hash
import pytz

# Create flask app
app = Flask(__name__, template_folder='templates')
app.debug = True

# Create in-memory database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['EGM_SQLALCHEMY_DB']
app.config['SQLALCHEMY_ECHO'] = True
# Create dummy secrey key so we can use sessions
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_USERNAME'] = 'asmoor@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ['PASS']

mail = Mail(app)
db = SQLAlchemy(app)

@app.route('/')
def index():
    return render_template("home.html")


@app.route('/about')
def about():
    bios = db.session.query(Biography).all()
    bio_text = ""
    for bio in bios:
        bio_text = bio.text
    return render_template("about.html",bio_text=bio_text)


@app.route('/work')
def work():
    works = db.session.query(Work).order_by(Work.work_date.desc()).all()
    return render_template("work.html", works=works)


@app.route('/events')
def events():
    events = db.session.query(Event).order_by(Event.event_date.desc()).all()
    upcoming_list = []
    for event in events:
        upcoming_list.append(str(datetime.now(pytz.utc)) < event.event_date)
    events_and_upcoming = zip(events, upcoming_list)
    return render_template("events.html", events_and_upcoming=events_and_upcoming, events_and_upcoming_reversed = events_and_upcoming[::-1])


@app.route('/blog')
def blog():
    blogs = db.session.query(Blog).all()
    return render_template("blog.html", blogs=blogs)


@app.route('/contact', methods = ['GET','POST'])
def contact():
    if request.method == "POST":
        try:
            subject = request.form["subject"]
            sender = request.form["email"]
            body = request.form["message"]
            msg = Message(subject,
                      sender=sender,
                      recipients=["egmobbs@gmail.com"],
                      body=body)
            mail.send(msg)
        except:
            print "Oops!  Mail wasn't sent..."
    return render_template("contact.html")


class Blog(db.Model):
    __tablename__ = 'Blogs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String, unique=False)


class BlogAdmin(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()

    column_display_pk = True
    form_columns = ['text']


class Biography(db.Model):
    __tablename__ = 'Biographies'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String, unique=False)


class BiographyAdmin(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()
    
    form_overrides = dict(text=TextAreaField)
    column_display_pk = True
    form_columns = ['text']


class Work(db.Model):
    __tablename__ = 'Works'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    work_text = db.Column(db.UnicodeText, unique=False)
    work_type = db.Column(db.String, unique=False)
    work_date = db.Column(db.String, unique=False)


class WorkAdmin(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()
    
    form_overrides = dict(work_type=SelectField, work_text=TextAreaField)
    form_args = dict(
        work_type=dict(choices=[(u'PO', u'Poetry'), (u'PR', u'Project'), (u'OT', u'Other')]),
        work_date=dict(label='Event date (e.g. 2014-06-07 18:00:00)')
    )
    column_display_pk = True
    form_columns = ['work_text', 'work_type', 'work_date']


class Event(db.Model):
    __tablename__ = 'Events'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_title = db.Column(db.String, unique=False)
    event_description = db.Column(db.String, unique=False)
    event_date = db.Column(db.String, unique=False)
    event_date_text = db.Column(db.String, unique=False)


class EventAdmin(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()
    
    form_overrides = dict(event_description=TextAreaField)
    form_args = dict(
        event_date=dict(label='Date for backend (e.g. 2014-06-07 18:00:00)'),
        event_date_text=dict(label='Date how you want it displayed')
    )
    column_display_pk = True
    form_columns = ['event_title', 'event_description', 'event_date', 'event_date_text']


# Create user model.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(64))

    #def __init__(self, login, password):
    #    self.login =  login
    #    self.password = generate_password_hash(password)

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


class UserAdmin(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated()
    
    def on_model_change(self, form, model):
        model.password = generate_password_hash(form.password.data)

    column_display_pk = True
    column_exclude_list = ('password')
    form_columns = ['login', 'password']


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.TextField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
        # to compare plain text passwords use
        # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.TextField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized index view class that handles login & registration
class MyAdminIndexView(admin.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated():
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        print "login view!"
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated():
            return redirect(url_for('.index'))
        self._template_args['form'] = form
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


def create_data():
    """ A helper function to create our tables."""
    db.create_all()
    admin_user = User(os.environ['EGM_USER'], os.environ['EGM_PASS'])
    db.session.add(admin_user)
    db.session.commit()


# Initialize flask-login
init_login()

# Create admin interface
admin = admin.Admin(name="Create or edit content:", index_view=MyAdminIndexView(), base_template='admin_master.html')
admin.add_view(BlogAdmin(Blog, db.session))
admin.add_view(BiographyAdmin(Biography, db.session))
admin.add_view(EventAdmin(Event, db.session))
admin.add_view(WorkAdmin(Work, db.session))
admin.add_view(UserAdmin(User, db.session))
admin.init_app(app)

if __name__ == '__main__':
    if '-c' in sys.argv:
        create_data()
    else:
        # Start app
        app.run()