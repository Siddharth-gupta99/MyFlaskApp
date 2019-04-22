from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, Response
from data import Articles 
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from functools import wraps

app = Flask(__name__)   #app==> instance of Flask, __name__ ==> kind of placeholder for current module(here app.py)

# Config MySQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'  #Creating a cursor, using cursor we can execute the query,[key value pairs==>Dictionary]

#init MySQL
mysql=MySQL(app)

# Articles = Articles()

#Index
@app.route('/')
def index():
	return render_template('home.html')

#About
@app.route('/about')
def about():
	return render_template('about.html')

#Articles
@app.route('/articles')
def articles():

	#create cursor
	cur=mysql.connection.cursor()

	#Get Articles
	result=cur.execute("SELECT * FROM articles")

	articles=cur.fetchall()

	if result > 0:
		return render_template ('articles.html', articles=articles)
	else:
		msg='No Articles Found'
		return render_template ('articles.html', msg=msg)
	return render_template('articles.html', articles=Articles)

#Single Article 
@app.route('/article/<string:id>')
def article(id):

	#create cursor
	cur=mysql.connection.cursor()

	#get Article
	result=cur.execute("SELECT * FROM articles where id=%s", [id])

	article=cur.fetchone()

	return render_template('article.html', article=article)


#Registration Form class
class RegisterForm(Form): #Subclass of Form
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=5, max=50)])
	email = StringField('Email', [validators.Length(min=5, max=50)])
	password = PasswordField('Password', [validators.DataRequired(), validators.EqualTo('confirm', message='Passwords do not match')])
	confirm = PasswordField('Confirm Password')

#User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method=='POST' and form.validate():
		name=form.name.data
		email=form.email.data
		username=form.username.data
		password=sha256_crypt.encrypt(str(form.password.data))

		# Check if username exists in database 
		cur=mysql.connection.cursor()
		result1=cur.execute("SELECT * FROM users where username=%s", [username])
		result2=cur.execute("SELECT * FROM users where email=%s", [email])
		# article=cur.fetchone()
		# query = "SELECT username FROM users WHERE username =%s"
		if result1>0:                                                
			flash('Username already exists', 'warning')
			# return render_template('register.html')
			return redirect(url_for('register'))
		if result2>0:
			flash('Registered with this email already', 'warning')
			# return render_template('register.html')
			return redirect(url_for('register'))

		else:
		#create cursor
			cur=mysql.connection.cursor()

		#execute query
			cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

		#commit to DB
			mysql.connection.commit()

		#close connection
			cur.close()

			flash('You are registered and can log in.', 'success')
			return redirect(url_for('login'))

		# return render_template('register.html')
	return render_template('register.html', form=form)


#User login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method=='POST':  #If form is submitted
		#Not using WTForms

		username=request.form['username']
		candidate_password=request.form['password']

		#create cursor
		cur=mysql.connection.cursor()

		#Fetch user by username
		result = cur.execute("SELECT * FROM users where username = %s", [username])

		if result > 0:
			#Get stored hash 
			data=cur.fetchone() # fetch only one(first one) if there are multiple same username
			password=data['password']

			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				#Passed, Now create a session Variable
				# app.logger.info('Password Matched')
				session['logged_in'] = True
				session['username'] = username

				flash('You are logged in', 'success')
				return redirect(url_for('dashboard'))

			else:
				error = 'Invalid Login' 
				return render_template('login.html', error=error)
				# app.logger.info('Password Not Matched')

			cur.close()
		else:
			error = 'Username Not Found'
			return render_template('login.html', error=error)

			# app.logger.info('No such User') ==> give info on terminal

	return render_template('login.html')



#Check if user logged in
def is_logged_in(f):   # can be used with any route 
	@wraps(f) 				#Decorator
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap


#LogOut
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

	#create cursor
	cur=mysql.connection.cursor()

	#Get Articles
	result=cur.execute("SELECT * FROM articles")

	articles=cur.fetchall()

	if result > 0:
		return render_template ('dashboard.html', articles=articles)
	else:
		msg='No Articles Found'
		return render_template ('dashboard.html', msg=msg)


#Article Form class
class ArticleForm(Form): #Subclass of Form
	title = StringField('Title', [validators.Length(min=5, max=200)])
	body = TextAreaField('Body', [validators.Length(min=30)])
	

#Add article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method=='POST' and form.validate():
		title=form.title.data
		body=form.body.data

		#create cursor
		cur=mysql.connection.cursor()

		#execute query
		cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

		#commit to DB
		mysql.connection.commit()

		#close connection
		cur.close()

		flash('Article Created', 'success')
		return redirect(url_for('dashboard'))

		# return render_template('register.html')
	return render_template('add_article.html', form=form)


#Edit article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	#To get the article by id we need to do a query and then fill a form

	#create cursor
	cur=mysql.connection.cursor()

	#get Article by id
	result=cur.execute("SELECT * FROM articles where id=%s", [id])

	article=cur.fetchone()

	#Get form
	form = ArticleForm(request.form)

	#Populate the article form fields
	form.title.data=article['title']
	form.body.data=article['body']

	if request.method=='POST' and form.validate():
		title=request.form['title']
		body=request.form['body']
		#create cursor
		cur=mysql.connection.cursor()

		#execute query
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

		#commit to DB
		mysql.connection.commit()

		#close connection
		cur.close()

		flash('Article Updated', 'success')
		return redirect(url_for('dashboard'))

		# return render_template('register.html')
	return render_template('edit_article.html', form=form)

#Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	#Create Cursor
	cur=mysql.connection.cursor()

	#Execute
	cur.execute("DELETE FROM articles WHERE id=%s", [id])

	#commit to DB
	mysql.connection.commit()

	#close connection
	cur.close()

	flash('Article Deleted', 'success')
	return redirect(url_for('dashboard'))

if __name__=='__main__': #Check whether that script is going to be executed or not
	app.secret_key='HailHydra123456'
	app.run(debug=True)
