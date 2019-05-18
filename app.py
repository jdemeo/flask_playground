from flask import Flask, render_template, flash, redirect, url_for, session,\
logging, request
# from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


# Place holder for current module
app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'jdemeo'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

# Articles = Articles()

"""ROUTES"""
@app.route('/')
def index():
    # Looks for template in templates dir
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Articles
@app.route('/articles')
def articles():
    # # articles = Articles just passes the data to the template
    # return render_template('articles.html', articles = Articles)

    # Create cursors
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)

    # Close connection
    cur.close()

# Want a string that comes from the parameters id
@app.route('/article/<string:id>/')
def article(id):
    # Create cursors
    cur = mysql.connection.cursor()

    # Get article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    return render_template('article.html', article=article)


'''NEED TO CREATE A CLASS FOR EACH FORM'''
# Registration form
class RegisterForm(Form):
    # Fields
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# USER REGISTRATION
# Excepts GETs and POSTs
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    # Form is submitted and valid inputs
    if request.method == 'POST' and form.validate():
        # Get form data
        name = form.name.data
        email = form.email.data
        username = form.username.data
        # Need to encrypt first
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor; used to execute commands
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password)\
            VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close Connection
        cur.close()
        # Display message
        flash('You are now registered and can log in', 'success')

        # Returns to homescreen
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

# USER LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form fields; different than registration form
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result =  cur.execute('SELECT * FROM users WHERE username = %s',
            [username])

        # If entry is found
        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                # Success message
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')

# Check if user logged in by using a 'decorator'
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            # Error message
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout user
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# User dashboard
@app.route('/dashboard')
# Check if user is logged_in
@is_logged_in
def dashboard():
    # Create cursors
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()   # fetch in dictionary form
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)

    # Close connection
    cur.close()

# Article form
class ArticleForm(Form):
    # Fields
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# ADD ARTICLE
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)

    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",\
            (title, body, session['username']))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()
        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# EDIT ARTICLE
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id=%s", [id])
    article = cur.fetchone()

    # Close connection
    cur.close()

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()
        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# DELETE ARTICLE
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id=%s", [id])

    # Commit to DB
    mysql.connection.commit()

    # Close connection
    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))


# Check if this is the script to be executed
if __name__ == '__main__':
    app.secret_key='secret123'
    # Start/run application
    # @debug: True allows for saving file and reloading routes without
    # restarting connection
    app.run(debug=True)
