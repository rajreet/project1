import os

from flask import Flask, session, render_template,request,redirect, url_for, escape,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from hashlib import md5
import string
import requests
import json
from pprint import pprint

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():	
	if 'username' in session:
		return redirect(url_for('loginuser'))
	return render_template("index.html")
	
@app.route("/register", methods=["GET","POST"])

def register():
	return render_template("register.html",message=" ")
	
@app.route("/register/success", methods=["POST"])
def success():
	name=request.form.get("name")
	email=request.form.get("email")
	username=request.form.get("username")
	password=request.form.get("password")
	
	print(name)
	if name is "":
		return render_template("register.html",msg_name="The given field cannot be null")
		
	if email is "":
		return render_template("register.html",msg_email="The given field cannot be null")
		
	if username is "":
		return render_template("register.html",msg_username="The given field cannot be null")
		
	if password is "":
		return render_template("register.html",msg_password="The given field cannot be null")

	un = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
	
	if un !=None:
		return render_template("register.html",msg_username="The username already exists!")
			
	db.execute("INSERT INTO users(name,username,password,email) VALUES (:name, :username, :password, :email)",
		{"name": name, "username": username, "password": password, "email": email})
	db.commit()
	return render_template("message.html",heading="Account Created!",message=" ")
	   
@app.route("/login")
def login():
	if 'username' in session:
		return redirect(url_for('loginuser'))
	return render_template("login.html",message=" ")
	
	
@app.route("/loginerror",methods=["POST"])
def loginerror():
	
	if 'username' in session:
		return redirect(url_for('loginuser'))
			
	else:
		username=request.form.get("username")
		password=request.form.get("password")
		

		un = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
	
		if un is None:
			return render_template("login2.html",message="Invalid Username.")
	
		else:
			pwd = db.execute("SELECT password FROM users WHERE username = :username", {"username": username}).fetchall()
		
			for row in pwd:
				if password==row[0]:
					session['username']=username
					return redirect(url_for('loginuser'))
				else:
					return render_template("login2.html",message="Incorrect Password")
				
@app.route("/login/user",methods=["POST","GET"])
def loginuser():
	if 'username' in session:
		username= escape(session['username'])
		nm=db.execute("SELECT name FROM users WHERE username=:username",{"username":username}).fetchall()
		for row in nm:
			name=row[0]
		return render_template("user.html",name=name)
		
	return redirect(url_for('login'))

@app.route("/logout")
def logout():
	session.pop('username',None)
	return render_template("message.html",heading="Logged Out!",message=" ")
	
@app.route("/login/user/book" )
def searchbook():
	
	bookname=request.args.get("search")
	
	name="%"+ string.capwords(bookname) +"%"
	
	booklist=db.execute("SELECT * FROM books WHERE isbn LIKE :name OR title LIKE :name OR author LIKE :name",{"name":name}).fetchall()
			
	return render_template("booklist.html",booklist=booklist)
	
@app.route("/book/<string:isbn>",methods=["POST","GET"])
def book(isbn):
	rating=None
	review=None
	bookname=db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	
	if bookname is None:
		return render_template("error.html")
		
	if request.method=="POST":
		review=request.form.get("review")
		rating=request.form.get("star")

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "gmaVsowZsITzZGWKQjQ3sQ", "isbns": isbn})
	data=res.json()
	gr_rating=data["books"][0]["average_rating"]
	count=data["books"][0]["work_ratings_count"]
	
	username=escape(session['username'])

	if rating != "" and rating!= None:
		db.execute("INSERT INTO ratings (username, isbn, rating) VALUES (:username, :isbn,:rating) ON CONFLICT (username,isbn) DO UPDATE SET rating=:rating ",{"username": username,"isbn":isbn,"rating":rating})
		
		db.commit()
		print(rating)
		
	name=db.execute("SELECT name FROM users WHERE username=:username",{"username":username}).fetchall()
	for row in name:
		nm=row[0]
		
	if review != "" and review!=None:	
		db.execute("INSERT INTO reviews (review, isbn, name) VALUES (:review, :isbn,:name) ON CONFLICT (name,isbn) DO UPDATE SET review =:review ",{"name": nm,"isbn":isbn,"review":review})

		db.commit()
	
	
	
	reviews=db.execute("SELECT * FROM reviews WHERE isbn=:isbn",{"isbn":isbn})
	
	r=db.execute("SELECT avg(rating) FROM ratings WHERE isbn=:isbn",{"isbn":isbn}).fetchall()
	for row in r:
		if row[0]!=None:
			rat='%.1f' % row[0]
		else:
			rat=3.0
	
	if float(rat)>=3.5:
		color="success"
	elif float(rat)>2.5:
		color="warning"
	else:
		color="danger"
	
	#with open("https://www.goodreads.com/book/review_counts.json", params={"key": "gmaVsowZsITzZGWKQjQ3sQ", "isbn": isbn }) as f:
	#	data = json.load(f)
		
	#	gr_rating=data["average_rating"]
	return render_template("book.html",bookname=bookname,reviews=reviews,name=name,r=rat,color=color,rating=rating,gr_rating=gr_rating,count=count)	

@app.route("/api/<string:isbn>")
def api_book(isbn):
	bookname=db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	
	if bookname is None:
		return jsonify({"error":"Invalid isbn"}),422
			
	review_count=db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
	if review_count is None:
		review_count=0
		
	r=db.execute("SELECT avg(rating) FROM ratings WHERE isbn=:isbn",{"isbn":isbn}).fetchall()
	for row in r:
		if row[0]!=None:
			rat='%.1f' % row[0]
		else:
			rat=3.0
			
	return jsonify({
						"Title":bookname.title,
						"Author":bookname.author,
						"Year":bookname.year,
						"isbn":bookname.isbn,
						"review_count":review_count,
						"average_rating":rat
						})	
		
	
	
	
if __name__ == '__main__':
    main()
