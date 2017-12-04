import os
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
import random
from flask_migrate import Migrate, MigrateCommand

##################### TASK 1 #####################
# Add import statements required for login

# Configure base directory of app
basedir = os.path.abspath(os.path.dirname(__file__))

# Application configurations
app = Flask(__name__)
app.static_folder = 'static'
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/giphydb"  # TODO: decide what your new database name will be, and create it in postgresql, before running this new application
# Lines for db setup so it will work as expected
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set up Flask debug and necessary additions to app
manager = Manager(app)
db = SQLAlchemy(app) # For database use
migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand) # Add migrate command to manager


##################### TASK 2 #####################
# Create a LoginManager object and configure its properties


## Set up Shell context so it's easy to use the shell to debug
# Define function
def make_shell_context():
    return dict( app=app, db=db)
# Add function use to manager
manager.add_command("shell", Shell(make_context=make_shell_context))

## NOTE ON MIGRATION SETUP
## You will get the following message when running command to create migration folder, e.g.:
## python main_app.py db init
## -->
# Please edit configuration/connection/logging settings in ' ... migrations/alembic.ini' before proceeding
## This is what you are supposed to see!

#########
######### Everything above this line is important/useful setup, not mostly application-specific problem-solving.
#########

##### Set up Models #####

# Set up association Table between artists and albums
# Set up association Table between search terms and GIFs
tags = db.Table('tags',db.Column('search_id',db.Integer, db.ForeignKey('search.id')),db.Column('gif_id',db.Integer, db.ForeignKey('gifs.id')))

# Set up association Table between GIFs and collections prepared by user
user_collection = db.Table('user_collection',db.Column('user_id', db.Integer, db.ForeignKey('gifs.id')),db.Column('collection_id',db.Integer, db.ForeignKey('personalCollections.id')))

# Special model for users to log in
class User(UserMixin, db.Model):
    __tablename__ = "users"
    ##################### TASK 3 #####################
    #### Enter the fields to setup the model
    # id - Primary key, integer
    # email - String (64 characters), unique = True, index = True
    # username - String (64 characters), unique = True, index = True
    # password - String (64 characters)
    # collectionID - Foreign key, integer --→ NOTE : The foreign key points to the id field in PersonalCollection model

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


# Other models
# Similar to playlists... a user can create his/ehr
class PersonalCollection(db.Model):
    __tablename__ = "personalCollections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    gifs = db.relationship('Gif',secondary=user_collection,backref=db.backref('personalCollections',lazy='dynamic'),lazy='dynamic')

class Gif(db.Model):
    __tablename__ = "gifs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))

    def __repr__(self):
        return "Title: {} & URL: {}".format(self.title,self.embedURL)

class Search(db.Model):
    __tablename__ = "search"
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(32),unique=True) # Only unique searches
    gifs = db.relationship('Gif',secondary=tags,backref=db.backref('search',lazy='dynamic'),lazy='dynamic')

    def __repr__(self):
        return "{} : {}".format(self.id, self.term)

## DB load functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # returns User object or None


##### Set up Forms #####

class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    #Additional checking methods for the form
    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class GifSearchForm(FlaskForm):
    search = StringField("Enter a term to search GIFs", validators=[Required()])
    submit = SubmitField('Submit')

##### Helper functions

### For database additions / get_or_create functions

def get_gif_by_id(id):
    """returns song or None"""
    g = Gif.query.filter_by(id=id).first()
    return g

def get_or_create_search_term(db_session, term, gif_list = []):
    searchTerm = db_session.query(Search).filter_by(term=term).first()
    if searchTerm:
        print("Found term")
        return searchTerm
    else:
        print("Added term")
        searchTerm = Search(term=term)
        for g in gif_list:
            gif = get_or_create_gif(db_session, title = g[1], url = g[2])
            searchTerm.gifs.append(gif)
        db_session.add(searchTerm)
        db_session.commit()
        return searchTerm

def get_or_create_gif(db_session, title, url):
    gif = db_session.query(Gif).filter_by(title = title).first()
    if gif:
        return gif
    else:
        gif = Gif(title = title, embedURL = url)
        db_session.add(gif)
        db_session.commit()
        return gif

def get_or_create_personal_collection(db_session, name, gif_list, current_user):
    gifCollection = db_session.query(PersonalCollection).filter_by(name=name,user_id=current_user.id).first()
    if gifCollection:
        return gifCollection
    else:
        gifCollection = PersonalCollection(name=name,user_id=current_user.id,gifs=[])
        for g in gif_list:
            gifCollection.gifs.append(g)
        db_session.add(gifCollection)
        db_session.commit()
        return gifCollection


##### Set up Controllers (view functions) #####

## Error handling routes
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

## Login routes
@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
    return "Only authenticated users can do this! Try to log in or contact the site admin."



## Main routes
@app.route('/', methods=['GET', 'POST'])
def index():
    gifs = Gif.query.all()
    num_gifs = len(gifs)
    form = GifSearchForm()
    if form.validate_on_submit():
        if db.session.query(Search).filter_by(term=form.search.data).first():
            pass #### Remove pass when you start task 5
            ##################### TASK 5 #####################
            #### Write code for retrieving the search term from the database, and displaying all the GIFs associated with it.
            #### You can render template all_gifs.html to display the GIFs title and the GIF
        else:
            # request GIFs from the API for that search term, add the search term and GIFs to database
            baseURL = "https://api.giphy.com/v1/gifs/search"
            params_diction = {}
            params_diction['api_key'] = "" #Enter your API Key here...
            params_diction['q']=form.search.data
            params_diction['limit'] = 5 ### Can change the limit if you would like

            ##################### TASK 5 #####################
            #### Write code for requesting data and adding the search term and GIFs to the tables
            #### After adding the GIFs, display them using all_gifs.html

    return render_template('index.html', form=form, num_gifs=num_gifs)

@app.route('/all_gifs')
def see_all():
    all_gifs = [] # To be tuple list of title, genre
    gifs = Gif.query.all()
    for g in gifs:
        all_gifs.append((g.title,g.embedURL))
    return render_template('all_gifs.html', all_gifs=all_gifs)

@app.route('/create_gif_collection',methods=["GET","POST"])
@login_required
def create_gif_collection():
    form = CollectionCreateForm()
    choices = []
    for g in Gif.query.all():
        choices.append((g.id, g.title))
    form.gif_picks.choices = choices
    if form.validate_on_submit():
        pass #### Remove pass when you start task 6
        ##################### TASK 6 #####################
        #### Retrieve the name of the collection from the form data and store it in a variable collectionName
        #### Retrieve the gifs selected from the form data and store it in a variable gifSelected
        #### Print the gifSelected... it should like a list of numbers. These numbers are the IDs of the GIF user had selected
        #### Use the get_gif_by_id function to get each GIF object by its ID. Accumulate all the GIF objects in a variable gif_objects
        #### Now call get_or_create_personal_collection with these parameters : db.session, current_user, collectionName, gif_objects
        #### If all goes successfully, return "Collection {} was made".format(collectionName)
    return render_template('create_gif_collection.html',form=form)


if __name__ == '__main__':
    db.create_all()
    manager.run() # NEW: run with this: python main_app.py runserver
    # Also provides more tools for debugging
