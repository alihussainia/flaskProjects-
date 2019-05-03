from flask import Flask , render_template , url_for , request , redirect , flash , session
import wtforms
from wtforms import StringField , TextAreaField , PasswordField , Form , validators
from flask_mysqldb import MySQL
from functools import wraps
from passlib.hash import sha256_crypt
import json
import feedparser
from urllib.request import urlopen
from urllib.request import quote
import urllib3
from bs4 import BeautifulSoup
import bs4
app = Flask(__name__)

CURRENCY_URL = "https://openexchangerates.org//api/latest.json?app_id=6a0f7b96a90f4ed98578d79648afd01a"
#DataBase Connection MySQL Xampp

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'zakat'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


mysql = MySQL(app)


#is_required decorator
def is_logged_in(f):
  @wraps(f)
  def wrap(*args , **kwargs):
    if 'logged_in' in session:
      return f(*args , **kwargs)
    else:
      flash("Unauthorized Access! Please Login!" , 'danger')
      return redirect(url_for('login'))
  return wrap

# ================================INDEX PAGE===================================

@app.route('/')
def index():
  return render_template('index.html')


# ================================INFORMATION PAGE===================================

@app.route('/information')
def information():
  return render_template('information.html')

# ================================CALCULATE ZAKAT FORM CLASS===================================
class CalculateZakat(Form):
  gold = StringField('Gold in (Cash)' ,[validators.length(min=2 , max=30)])
  silver = StringField('Silver in (Cash)' ,[ validators.length(min=2 , max=30)])
  cash = StringField('Cash in Hand' , [validators.length(min=5 , max= 30)])
  properties = StringField('Property in (Cash)' ,[ validators.length(min=2 , max=30)])
  liabilities = StringField('Liabilities in (Cash)' , [validators.length(min=5 , max= 30)])

# ================================CALCULATE ZAKAT PAGE===================================


def get_rate(frm, to):
    all_currency = urlopen(CURRENCY_URL).read()
    parsed = json.loads(all_currency).get('rates')
    frm_rate = parsed.get(frm.upper())
    to_rate = parsed.get(to.upper())
    return (to_rate / frm_rate, parsed.keys())

class CurrencyCoverter(Form):
  amount = StringField('Enter Amount' ,[validators.length(min=2 , max=30)])
  convert = StringField( [validators.DataRequired(), validators.length(min=2 , max=30)])

@app.route('/calculate' ,methods = ['GET' , 'POST'])
def calculate():
  currnecy_form = CurrencyCoverter(request.form)
  if request.method == "POST" or request.method == "GET":
    amount = currnecy_form.amount.data
    convert = currnecy_form.convert.data


  DEFAULTS = {'publication': 'bbc',
            'city': 'London,UK',
            'currency_from': 'GBP',
            'currency_to': 'USD'
            }
  form = CalculateZakat(request.form)
  # ====================================================CURRENCY CONVERTER=======================================================
  currency_from = request.args.get("currency_from")
  if not currency_from:
      currency_from = DEFAULTS['currency_from']
  currency_to = request.args.get("currency_to")
  if not currency_to:
      currency_to = DEFAULTS['currency_to']
  rate, currencies = get_rate(currency_from, currency_to)
  return render_template("calculate.html",currency_from=currency_from, currency_to=currency_to, rate=rate, currencies=sorted(currencies) , form = form , currnecy_form = currnecy_form)

# ============================================================FORM=================================
  if request.method == "POST" and form.validate():

    gold = int(form.gold.data)
    silver = int(form.silver.data)
    cash = int(form.cash.data)
    properties =  int(form.properties.data)
    liabilities =  int(form.liabilities.data)

    if (gold < 10000) and (silver < 10000) and (cash < 10000) and (properties < 10000) and (liabilities < 10000):
      return render_template('not-eligible.html')
    else:
      zakat = (gold + silver + cash + properties + liabilities)//2.5
      return render_template('zakat.html' , zakat = zakat , currnecy_form = currnecy_form)





  return render_template('calculate.html' , form = form)

# ================================CALCULATE ZAKAT PAGE===================================
#REGISTRATION FORMS START

class RegistrationForm(Form):
  name = StringField('Name' ,[validators.length(min=2 , max=30)])
  username = StringField('Username' ,[validators.DataRequired(), validators.length(min=2 , max=30)])
  email = StringField('email' , [validators.length(min=5 , max= 30) ,  validators.Email() , validators.DataRequired()])
  password = PasswordField('password' ,[validators.DataRequired(),validators.length(min=2 , max=30),
  validators.DataRequired(),
  validators.EqualTo('confirm' , message='Password Must Match')])
  confirm = PasswordField('Comfrim Password' , [validators.DataRequired()])


# ================================REGISTRATION PAGE===================================

@app.route('/registration' , methods = ['GET' , 'POST'])
def registration():

  form = RegistrationForm(request.form)

  if request.method == "POST" and form.validate():
    name = form.name.data
    username = form.username.data
    email = form.email.data
    password =  form.password.data

    cur = mysql.connection.cursor()

    cur.execute("INSERT into Users (name , username , email , password) VALUES (%s , %s ,%s ,%s)" , (name , username , email , password))

    mysql.connection.commit()

    cur.close()

    return redirect(url_for('index'))

  return render_template('registration.html' , form = form)

#REGISTRATION FORMS END

# ================================LOGIN FORMS PAGE===================================

#LOGIN FORMS START

class LoginForm(Form):
  username = StringField('Username' ,[validators.length(min=2 , max=30)])
  password = PasswordField('password' ,[validators.length(min=2 , max=30)])

@app.route('/login' , methods = ['GET' , 'POST'])
def login():
  form = LoginForm(request.form)

  if request.method == 'POST':
    username = request.form['username']
    password_candid = request.form['password']

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM Users WHERE username = %s " , [username])

    if result > 0:
      #GET HASH PASSWORD

      data = cur.fetchone()
      password = data['password']

      if password_candid == password:
        session['logged_in'] = True
        session['username'] = username

        flash("You are now register , You can now login" , 'success')
        return redirect(url_for('index'))
      else:
        flash("Invalid Login" , 'danger')
        return render_template('login.html' , form = form)
      cur.close()
    else:
      flash('User name Not Found Please Register Youself' , 'danger')
      return render_template('login.html', form = form)
  return render_template('login.html' , form = form)


#LOGIN FORMS ENDS


if __name__ == "__main__":
  app.secret_key = 'secret123'
  app.run(debug=True , port = 3000)
