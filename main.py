###############################################################################
# IMPORT FUNCTIONS
###############################################################################
from google.cloud import storage
import os
import re
import io
import random
from google.cloud import language_v1
from google.cloud import vision
from google.cloud import automl_v1beta1
from pil import Image
import sys
import pandas as pd
import string
import datetime
import requests
import json
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from pyzbar import pyzbar
from pyzbar.pyzbar import decode
#import cv2
import numpy as np
from werkzeug.exceptions import HTTPException, NotFound, BadRequestKeyError
from sqlalchemy.exc import IntegrityError
#from PIL import Image
# new import line
from flask_login import LoginManager, UserMixin, login_user, current_user
from flask_login import logout_user, login_required
import uuid
from flask_bootstrap import Bootstrap
from forms import RegistrationForm, LoginForm

# this file is missing because it is included in the gitignore. You have to
# create your own and fill it with the following variables
from secrets import SQL_PASSWORD, SQL_PUBLIC_IP, SQL_DATABASE_NAME, FOODREPO_KEY , SPOON_KEY ,PROJECT_ID,MODEL_ID, BUCKET_NAME ,SECRET_KEY
import spoonacular as sp
api = sp.API(SPOON_KEY)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./gcp_credentials/astral-charter-294311-a6531ff12b3e.json"
API_KEY = SPOON_KEY

app = Flask(__name__)

###############################################################################
# GOOGLE CLOUD SETTINGS
###############################################################################
GC_BUCKET_NAME = BUCKET_NAME

# Google Cloud SQL settings
PASSWORD = SQL_PASSWORD
PUBLIC_IP_ADDRESS = SQL_PUBLIC_IP
DBNAME = SQL_DATABASE_NAME

# Configuration
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://postgres:{PASSWORD}@{PUBLIC_IP_ADDRESS}/{DBNAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True


###############################################################################

bcrypt = Bcrypt(app)

login_manager = LoginManager(app)

login_manager.login_view = "login"

# --- BOOTSTRAP CONFIGURATION --- #
Bootstrap(app)

vision_client = vision.ImageAnnotatorClient()
###############################################################################
# Database configuration
###############################################################################


db = SQLAlchemy(app)
db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)


    password = db.Column(db.Binary(100), nullable=False)
    products = db.relationship("Products", backref="vendor", lazy=True)
    img_public_url = db.Column(db.String, nullable=False , default='https://storage.cloud.google.com/ascet-fashion-showroom-inclass/WhatsApp%20Image%202020-11-30%20at%2014.06.45.jpeg')
    img_gcs_path = db.Column(db.String, nullable=False , default = 'gs://ascet-fashion-showroom-inclass/WhatsApp Image 2020-11-30 at 14.06.45.jpeg')
        # Code
    liked = db.relationship('ProductsLike',foreign_keys='ProductsLike.user_id',backref='user', lazy='dynamic')

    def like_products(self,products):
        if not self.has_liked_products(products):
            like = ProductsLike(user_id=self.id, products_id=products.id)
            db.session.add(like)

    def unlike_products(self, products):
        if self.has_liked_products(products):
            ProductsLike.query.filter_by(
                user_id=self.id,
                products_id=products.id).delete()

    def has_liked_products(self, products):
        return ProductsLike.query.filter(
            ProductsLike.user_id == self.id,
            ProductsLike.products_id == products.id).count() > 0

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"User(id: '{self.id}', name: '{self.name}', " +\
               f" email: '{self.email}')"




class Products(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)
    description = db.Column(db.String(2000), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    tag = db.Column(db.String(30), unique=False, nullable=False)
    post_length = db.Column(db.Integer, nullable=False)

    sentiment = db.Column(db.Integer, nullable=False)
    magnitude = db.Column(db.Integer, nullable=False)
    language = db.Column(db.String(50), unique=False, nullable=False)
    pop_word = db.Column(db.String(50), unique=False, nullable=False)
    occurence = db.Column(db.Integer, nullable=False)


    # we can set default values manually or by adding a function (without
    # brackets because otherwise we would be calling it)
    date_created = db.Column(db.DateTime, nullable=False,
                             default=datetime.datetime.now)
    img_public_url = db.Column(db.String, nullable=False)
    img_gcs_path = db.Column(db.String, nullable=False)
    likes = db.relationship('ProductsLike', backref='products', lazy='dynamic')
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"Product(id: '{self.id}', name: '{self.name}', description:" +\
               f" '{self.description}', price: '{self.price}', tag: '{self.tag}',post_length: '{self.post_length}',date_created" +\
               f": '{self.date_created}', public_url: '{self.img_public_url}',sentiment: '{self.sentiment}', magnitude: '{self.magnitude}', language: '{self.language}',pop_word: '{self.pop_word}'" +\
               f"  , occurence: '{self.occurence}', gcs_path: '{self.img_gcs_path}', vendor: '{self.user_id}')"

class ProductsLike(db.Model, UserMixin):
    __tablename__ = 'products_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    products_id = db.Column(db.Integer, db.ForeignKey('products.id'))

class Food(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, nullable=False)
    grocery_list = db.Column(db.String(1000), unique=False, nullable=False)
    recipe_title = db.Column(db.String(200), unique=False, nullable=False)

    # we can set default values manually or by adding a function (without
    # brackets because otherwise we would be calling it)
    date_created = db.Column(db.DateTime, nullable=False,
                             default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"Food(id: '{self.id}', recipe_id: '{self.recipe_id}', grocery_list: '{self.grocery_list}', " +\
               f" date_created" +\
               f": '{self.date_created}',recipe_title: '{self.recipe_title}'," +\
               f" vendor: '{self.user_id}')"


class Menu(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    spoon_id = db.Column(db.Integer, nullable=False)
    dish_title = db.Column(db.String(300), unique=False, nullable=False)
    day = db.Column(db.String(30), unique=False, nullable=False)
    slot = db.Column(db.String(30), unique=False, nullable=False)
    #recipe_title = db.Column(db.String(50), unique=True, nullable=False)

    # we can set default values manually or by adding a function (without
    # brackets because otherwise we would be calling it)
    date_created = db.Column(db.DateTime, nullable=False,
                             default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"Food(id: '{self.id}', menu: '{self.menu}', spoon_id: '{self.spoon_id}'," +\
               f" date_created" +\
               f": '{self.date_created}',day: '{self.day}',slot: '{self.slot}'," +\
               f" vendor: '{self.user_id}')"



class Custom(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    product = db.Column(db.String(300), unique=False, nullable=False)

    #recipe_title = db.Column(db.String(50), unique=True, nullable=False)

    # we can set default values manually or by adding a function (without
    # brackets because otherwise we would be calling it)
    date_created = db.Column(db.DateTime, nullable=False,
                             default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"Food(id: '{self.id}', product: '{self.product}', " +\
               f" date_created" +\
               f": '{self.date_created}'," +\
               f" vendor: '{self.user_id}')"
class Fridge(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    product = db.Column(db.String(300), unique=False, nullable=False)


    #recipe_title = db.Column(db.String(50), unique=True, nullable=False)

    # we can set default values manually or by adding a function (without
    # brackets because otherwise we would be calling it)
    date_created = db.Column(db.DateTime, nullable=False,
                             default=datetime.datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        """
        This is the string that is printed out if we call the print function
            on an instance of this object
        """
        return f"Fridge(id: '{self.id}', product: '{self.product}', " +\
               f" date_created" +\
               f": '{self.date_created}'," +\
               f" vendor: '{self.user_id}')"
###############################################################################
# ROUTES
###############################################################################
@app.route("/")
@login_required
def first():
    return render_template("first_page.html")

@app.route("/home")
def home():
    return render_template("first_page.html")

@app.route("/feed" , methods=["GET", "POST"])
@login_required
def index():
    products1 = get_products()

    users= User.query.all()
    products = Products.query.all()


    return render_template("index.html", products_df=products1, users_df=users,products_all=products)
@app.route('/like/<int:products_id>/<action>')
@login_required
def like_action(products_id, action):
    products = Products.query.filter_by(id=products_id).first_or_404()
    if action == 'like':
        current_user.like_products(products)
        db.session.commit()
    if action == 'unlike':
        current_user.unlike_products(products)
        db.session.commit()
    return redirect(request.referrer)
@app.route("/feed2/<tag>")
@login_required
def feed2(tag):
    products1 = get_products()
    users= User.query.all()
    products = Products.query.all()
    return render_template("feed2.html", products_df=products1, tag=tag ,users_df=users,products_all=products)
@app.route("/feed3/<user_id>")
@login_required
def feed3(user_id):

    products3 = get_products()
    users= User.query.all()
    products1 = pd.read_sql(Products.query.filter_by(user_id=user_id).statement, db.session.bind)
    products = Products.query.all()
    user_id=int(user_id)
    return render_template("feed3.html", products_df=products1, user_id=user_id ,users_df=users,products_all=products)


@app.route("/analytics")
@login_required
def analytics():

    return render_template("analytics.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegistrationForm()

    if form.validate_on_submit():
        registration_worked = register_user(form)
        if registration_worked:
            flash("Registration successful")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()

    if form.validate_on_submit():
        if is_login_successful(form):
            flash("Login successful")
            return redirect(url_for("home"))
        else:
            flash("Login unsuccessful, please check your credentials and try again")
            return redirect(url_for("register"))

    return render_template("login.html", form=form)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():

    if request.method == 'POST':
        try:
            flash("Product uploaded successfully")
            title = request.form['title']
            time = request.form['Time']
            recipe = request.form['Recipe']
            img = request.files['input1']
            add_product(title, time, recipe, img)
            return redirect(url_for("index"))
        except IntegrityError:
            flash("The image of your recipe was not recognized , please try with another recipe image")
            return redirect(url_for("upload"))


    return render_template("upload.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route('/fridge-suggestor', methods=['GET', 'POST'])
@login_required
def recipes():
    fridge = get_fridge()
    querry=''
    for index, row in fridge.iterrows():
         if row['user_id'] == current_user.id:
             querry += row['product'] + ","

    if request.method == 'POST':
        try:
            content = requests.get(
                "https://api.spoonacular.com/recipes/findByIngredients?ingredients=" +
                request.form['restaurant_name'] +
                "&apiKey=" + API_KEY)
            json_response = json.loads(content.text)
            print(json_response)
            return render_template("fridge-suggestor.html", response=json_response) if json_response != [] else render_template(
                "fridge-suggestor.html", response="")
        except BadRequestKeyError:
            content = requests.get(
                "https://api.spoonacular.com/recipes/findByIngredients?ingredients=" +
                querry +
                "&apiKey=" + API_KEY)
            json_response = json.loads(content.text)
            print(json_response)
            return render_template("fridge-suggestor.html", response=json_response) if json_response != [] else render_template(
                "fridge-suggestor.html", response="")

    else:
        return render_template("fridge-suggestor.html")


@app.route('/recipe/<recipe_id>', methods=['GET', 'POST'])
@login_required
def recipe(recipe_id):
    url = 'https://api.spoonacular.com/'
    ingedientsWidget = "recipes/{0}/ingredientWidget".format(recipe_id)
    equipmentWidget = "recipes/{0}/equipmentWidget".format(recipe_id)
    tastetWidget = "recipes/{0}/tasteWidget".format(recipe_id)

    recipe_headers = {


        'accept': "text/html"
    }
    querystring = {'apiKey': API_KEY, "defaultCss": "true", "showBacklink": "false"}
    querystring2 = {'apiKey': API_KEY, "defaultCss": "true"}
    response = requests.get("https://api.spoonacular.com/recipes/informationBulk?ids=" +
                            recipe_id+"&includeNutrition=true&apiKey="+API_KEY)
    response_nutrients = api.visualize_recipe_nutrition_by_id(id=recipe_id, defaultCss=True)
    response_ingredients = requests.request(
        "GET", url + ingedientsWidget, headers=recipe_headers, params=querystring).text
    response_equipment = requests.request(
        "GET", url + equipmentWidget, headers=recipe_headers, params=querystring).text
    response_taste = requests.request("GET", url + tastetWidget,
                                      headers=recipe_headers, params=querystring2).text
    response_nutrients = response_nutrients.text
    recipe_id1 = recipe_id

    list1 = ''
    response2 = json.loads(response.text)
    recipe_title = response2[0]['title']
    for entry in response2[0]['extendedIngredients']:
        list1 += str(entry['originalString'] + " , ")
    response2 = list1[:-2]
    if request.method == 'POST':
        flash("Recipe saved successfully")
        add_grocery(response2, recipe_title, recipe_id1)
        return render_template("recipe_details.html", recipe_id=json.loads(response.text), response_nutrients=response_nutrients, response_equipment=response_equipment, response_ingredients=response_ingredients, response_taste=response_taste)

    return render_template("recipe_details.html", recipe_id=json.loads(response.text), response_nutrients=response_nutrients, response_equipment=response_equipment, response_ingredients=response_ingredients, response_taste=response_taste)


@app.route("/my-profile", methods=['GET', 'POST'])
@login_required
def display_profile():
    """Display user profile of username, email, and bookmarked recipes."""
    grocery = get_grocery()
    menu = get_menu()
    custom = get_custom()
    fridge= get_fridge()
    products3 = get_products()
    users= User.query.all()
    products1 = pd.read_sql(Products.query.filter_by(user_id=current_user.id).statement, db.session.bind)
    products = Products.query.all()

    if request.method == 'POST':
        try:
            recipe_id = request.form["recipe_id"]
            flash("Grocery List deleted successfully")
            Food.query.filter_by(recipe_id=recipe_id).delete()
            db.session.commit()
            return redirect(url_for('display_profile'))
        except BadRequestKeyError:
            try:
                product = request.form['product']
                flash("Added product to your grocery list successfully")
                add_custom(product)
                return redirect(url_for('display_profile'))
            except BadRequestKeyError:
                try:
                    product_name = request.form['delete_custom']
                    flash("Deleted product from your grocery list successfully")
                    Custom.query.filter_by(product=product_name).delete()
                    db.session.commit()

                    return redirect(url_for('display_profile'))
                except BadRequestKeyError:
                    try:
                        product_id = request.form["delete_post"]
                        flash("Your recipe deleted successfully")
                        Products.query.filter_by(id=product_id ).delete()
                        db.session.commit()
                        return redirect(url_for('display_profile'))
                    except BadRequestKeyError:
                        return redirect(url_for('change_profile'))

    return render_template("user_profile.html",
                           name=current_user.name,
                           email=current_user.email,
                           id=current_user.id,
                           url=current_user.img_public_url,
                           grocery_df=grocery,
                           menu_df=menu,
                           custom_df=custom,
                           fridge_df=fridge,
                            products_df=products1 ,
                            users_df=users,
                            products_all=products)
    # bookmarked_recipes=g.current_user.recipes)

@app.route("/change-profile", methods=['GET', 'POST'])
@login_required
def change_profile():

    if request.method == 'POST':

        try:

            new_name = request.form['name']
            user = User.query.filter_by(id=current_user.id).first_or_404()

            user.name = new_name

            db.session.add(user)
            db.session.commit()
            return redirect(url_for('change_profile'))
        except BadRequestKeyError:
            try:

                new_email = request.form['email']
                user = User.query.filter_by(id=current_user.id).first_or_404()

                user.email = new_email

                db.session.add(user)
                db.session.commit()
                return redirect(url_for('change_profile'))
            except BadRequestKeyError:
                try:
                    new_password = request.form['password']
                    user = User.query.filter_by(id=current_user.id).first_or_404()
                    hashed_password = bcrypt.generate_password_hash(new_password)

                    user.password = hashed_password

                    db.session.add(user)
                    db.session.commit()
                    return redirect(url_for('change_profile'))
                except BadRequestKeyError:
                    img = request.files['input1']
                    user = User.query.filter_by(id=current_user.id).first_or_404()
                    image_as_bytes = img.read()
                    file_name=''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

                    public_url = upload_bytes_to_gcs(bucket_name=GC_BUCKET_NAME,
                                                     bytes_data=image_as_bytes,
                                                     destination_blob_name=file_name)

                    user.img_gcs_path = file_name
                    user.img_public_url = public_url

                    db.session.add(user)
                    db.session.commit()
                    return redirect(url_for('change_profile'))








    return render_template("change_profile.html",
                            name=current_user.name,
                            email=current_user.email)
        #admin = User.query.filter_by(id=str(current_user.id)).first()
        #dmin.name = "Artur"
        #db.session.flush()
        #db.session.commit()





@app.route("/fridge_main", methods=['GET', 'POST'])
@login_required
def fridge_main():
    return render_template("fridge_main.html")
@app.route("/fridge_manual", methods=['GET', 'POST'])
@login_required
def fridge_manual():
    fridge = get_fridge()
    if request.method == 'POST':
        try:
            product = request.form['product']
            flash("Added product to your fridge successfully")
            add_fridge(product)
            return redirect(url_for('fridge_manual'))
        except BadRequestKeyError:
            product_name = request.form['delete_custom']
            flash("Deleted product from your fridge successfully")
            Fridge.query.filter_by(product=product_name).delete()
            db.session.commit()
            return redirect(url_for('fridge_manual'))
    return render_template("manual_fridge.html",fridge_df=fridge, id=current_user.id)

@app.route("/fridge_image", methods=['GET', 'POST'])
@login_required
def fridge_image():
    return render_template("fridge_image.html")





@app.route("/menu-creator", methods=["GET", "POST"])
@login_required
def create_menu():

    if request.method == 'POST':
        diet1 = request.form["input2"]
        calories1 = request.form["input1"]
        exclude1 = request.form["input3"]
        if calories1 == "":
            calories1 = "None"
        if exclude1 == "":
            exclude1 = "None"
        if calories1 == 'None':
            calories1 = None
        if exclude1 == 'None':
            exclude1 = None
        if diet1 == 'Standard':
            diet1 = None

        listid = []
        listresponse2 = []
        response = api.generate_meal_plan(diet=diet1, exclude=exclude1, targetCalories=calories1)
        json1 = response.json()
        for k in json1['items']:
            k['value'] = json.loads(k['value'])
        json_response = json1['items']
        dict_time = {1: "Breakfast", 2: "Lunch", 3: "Dinner"}
        dict_day = {1: "Monday", 2: "Tuesday", 3: "Wednesday",
                    4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}

        return redirect(url_for("create_menu2", json_response=json_response, dict_time=dict_time, dict_day=dict_day))


        # add_product(form)

    return render_template("menu-creator.html")


@app.route("/menu-creator2/<json_response>/<dict_time>/<dict_day>", methods=["GET", "POST"])
@login_required
def create_menu2(json_response, dict_time, dict_day):
    import ast
    json_response = ast.literal_eval(json_response)
    dict_time = ast.literal_eval(dict_time)
    dict_day = ast.literal_eval(dict_day)

    if request.method == 'POST':
        dict_time = {1: "Breakfast", 2: "Lunch", 3: "Dinner"}
        dict_day = {1: "Monday", 2: "Tuesday", 3: "Wednesday",
                    4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
        # list1=""
        flash("Menu saved successfully")
        Menu.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        for entry in json_response:
            add_menu(entry['value']['title'], entry['value']['id'],
                     dict_time[entry['slot']], dict_day[entry['day']])
        # response2=list1[:-2]

        # add_menu(response2,unique_filename)
        # return render_template("menu-creator.html", response=json_response,dict_time=dict_time,dict_day=dict_day)

    return render_template("menu-creator2.html", response=json_response, dict_time=dict_time, dict_day=dict_day)


@app.route("/barcode", methods=["GET", "POST"])
@login_required
def barcode():

    if request.method == 'POST':
        try:
            flash("Searching through our barcode database")
            # decodes all barcodes from an image
            #image2 = form.image_upload.data
            image2 = request.files["input1"]
            image2 = Image.open(image2)
            #image2 = np.array(image2)
            decoded_objects = pyzbar.decode(image2)
            bar_str = ''
            for obj in decoded_objects:
                bar_str += str(obj.data)
            bar_str = bar_str[1:]
            bar_str = bar_str[1:]
            bar_str = bar_str[:-1]

            BASE_URL = 'https://www.foodrepo.org/api/v3'
            KEY = FOODREPO_KEY
            ENDPOINT = '/products/_search'

            url = BASE_URL + ENDPOINT

            query = {
                "query": {
                    "terms": {
                        "barcode": [
                            bar_str

                        ]
                    }
                }
            }
            headers = {
                'Authorization': "Token token=" + KEY,
                'Accept': 'application/json',
                'Content-Type': 'application/vnd.api+json',
                'Accept-Encoding': 'gzip,deflate'
            }

            r = requests.post(url, json=query, headers=headers)
            print('Status: ' + str(r.status_code))
            print(r.json())
            if r.status_code == 200:
                results = r.json()
                print('Number of products found: ' + str(results['hits']['total']))
                print('First few products...')
                for hit in results['hits']['hits']:
                    smth = '  ' + hit['_source']['display_name_translations']['en']
                    smth2 = hit['_source']['images'][0]['large']
                    return render_template("barcode.html", texts=smth, type=smth2)

        except BadRequestKeyError:
            product = request.form["product"]
            flash("Added product to your fridge successfully")
            add_fridge(product)
            return redirect(url_for('barcode'))



    return render_template("barcode.html")


@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def get_bot_response():

    if request.method == 'POST':
        list1 = []
        list1.append(request.form['restaurant_name'])
        content = requests.get(
            "https://api.spoonacular.com/food/converse?text=" +
            request.form['restaurant_name'] +
            "&apiKey=" + API_KEY)
        content2 = requests.get(
            "https://api.spoonacular.com/food/converse/suggest?query=" +
            request.form['restaurant_name'] + '&number=5'
            "&apiKey=" + API_KEY)

        json_response = json.loads(content.text)
        suggest_response = json.loads(content2.text)
        suggest = suggest_response["suggests"]["_"]
        print(json_response)
        json_response2 = json_response['answerText']
        json_response3 = json_response['media']
        for n in json_response3:
            n['link'] = ''.join(filter(lambda x: x.isdigit(), n['link']))
        list1.append(json_response2)
        print(json_response)
        return render_template("chatbot.html", response=json_response3, response2=json_response2, list1=list1, suggest=suggest) if json_response != [] else render_template(
            "chatbot.html", response="")
    else:
        return render_template("chatbot.html")



@app.route("/vision-api", methods=["GET", "POST"])
def vision_api():

    if request.method == 'POST':
        try:
            flash("Using our AI Vision")

            #return render_template("vision-api.html", fridges_df=fridges)

            #image = request.files["input1"]


            #img = np.array(img)



            #img=image

            image1 = request.files["input1"]

            url=save_pic(image1)

            #label=vision(url)
            label=detect_labels_uri(url)


            return render_template("vision-api.html",url=url , label=label)



        except BadRequestKeyError:
            product = request.form["product"]
            flash("Added product to your fridge successfully")
            add_fridge(product)
            return redirect(url_for('vision_api'))

    return render_template("vision-api.html")

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def register_user(form_data):

    def email_already_taken(email):
        if User.query.filter_by(email=email).count() > 0:
            return True
        else:
            return False

    if email_already_taken(form_data.email.data):
        flash("That email is already taken!")
        return False

    hashed_password = bcrypt.generate_password_hash(form_data.password.data)

    user = User(name=form_data.name.data,
                email=form_data.email.data,
                password=hashed_password)

    db.session.add(user)

    db.session.commit()

    return True
def add_user(name,email, password, img_gcs_path,img_public_url):



    hashed_password = bcrypt.generate_password_hash(password)

    user = User(name=name,
                email=email,
                img_gcs_path=img_gcs_path,
                img_public_url=img_public_url,
                password=hashed_password)

    db.session.add(user)

    db.session.commit()

    return True


def is_login_successful(form_data):

    email = form_data.email.data
    password = form_data.password.data

    user = User.query.filter_by(email=email).first()

    if user is not None:
        if bcrypt.check_password_hash(user.password, password):

            login_user(user)

            return True

    return False


def detect_labels_uri(uri):
    """Detects labels in the file located in Google Cloud Storage or on the
    Web."""
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri

    response = client.label_detection(image=image)
    labels = response.label_annotations
    label = ""

    if labels:
        if len(labels) < 5:
            for j in labels:
                label = label + ", " + j.description
        else:
            for i in range(5):
                label = label + ", " + labels[i].description
        label = label[1:]
    else:
        label = "No labels found"
    label = label.strip('][').split(', ')
    #result = []
    for n in label[:]:
        if n==" Cuisine" :
            label.remove(n)
        elif n=="Cuisine" :
            label.remove(n)
        elif  n==" Dish":
            label.remove(n)
        elif  n=="Dish":
            label.remove(n)
        elif n==" Food":
            label.remove(n)
        elif n=="Food":
            label.remove(n)
        elif n=="Ingredient":
            label.remove(n)
        elif n==" Ingredient":
            label.remove(n)



    #label=label[0]
    return label[0]

    for label in labels:
        print(label.description)

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))


def save_pic(img):

    image_as_bytes = img.read()
    file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))

    public_url = upload_bytes_to_gcs(bucket_name=GC_BUCKET_NAME,
                                     bytes_data=image_as_bytes,
                                     destination_blob_name=file_name)


    img_public_url=public_url
    img_gcs_path=file_name

    return public_url

def automl(uri):
    project_id = PROJECT_ID
    model_id = MODEL_ID
    prediction_client = automl_v1beta1.PredictionServiceClient()


    # Get the full path of the model.
    model_full_id = automl_v1beta1.AutoMlClient.model_path(
        project_id, "us-central1", model_id
    )
    '''
    urllib.request.urlretrieve(uri, "sample.png")

    with open(uri, "rb") as content_file:
        content = content_file.read()'''

    response = requests.get(uri)
    content=response.content
    image = automl_v1beta1.Image()

    image = automl_v1beta1.Image(image_bytes=content)



    payload = automl_v1beta1.ExamplePayload(image=image)


    request = automl_v1beta1.PredictRequest(
        name=model_full_id,
        payload=payload
    )

    response = prediction_client.predict(request=request)
    for result in response.payload:

        return result.display_name




def add_product(title, time, recipe, img):

    image_as_bytes = img.read()
    file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    public_url = upload_bytes_to_gcs(bucket_name=GC_BUCKET_NAME,
                                     bytes_data=image_as_bytes,
                                     destination_blob_name=file_name)
    print(public_url)
    post_length=len(recipe)
    tag=automl(public_url)
    sentim, mag, lang = sent(recipe)
    pop_worde , occurence=pop_word(recipe)

    product = Products(name=title,
                       description=recipe,
                       price=time,
                       user_id= current_user.id,
                       tag=tag,
                       post_length=post_length,
                       sentiment=sentim,
                       magnitude=mag,
                       language=lang,
                       pop_word=pop_worde,
                       occurence=occurence,
                       img_public_url=public_url,
                       img_gcs_path=file_name)

    db.session.add(product)

    db.session.commit()
def analyse_sentiment(text):
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    result = client.analyze_sentiment(request={'document': document})

    text_sentiment = round(result.document_sentiment.score, 2)
    sentiment_magnitude = round(result.document_sentiment.magnitude, 2)
    language = result.language

    return text_sentiment, sentiment_magnitude, language

def sent(recipe):
    for text in [recipe]:
        sent, mag, lang = analyse_sentiment(text)
        sent=float(sent)
        mag=float(mag)
        lang=str(lang)
        return sent, mag, lang


def pop_word(recipe):
    client = language_v1.LanguageServiceClient()

    document = language_v1.Document(content=recipe, type_=language_v1.Document.Type.PLAIN_TEXT)

    response = client.analyze_syntax(request = {'document': document})

    list2=[]

    for token in response.tokens:
        list2.append(token.lemma)

    from collections import Counter
    c = Counter(list2)
    list2=c.most_common(1)
    pop_word=list2[0][0]
    occurence=list2[0][1]
    pop_word=str(pop_word)
    occurence=int(occurence)
    return pop_word , occurence
def add_custom(form_data):

    cgrocery = Custom(product=form_data,
                      user_id=current_user.id,
                      )

    db.session.add(cgrocery)

    db.session.commit()
def add_fridge(form_data):

    fridge = Fridge(product=form_data,
                      user_id=current_user.id,
                      )


    db.session.add(fridge)

    db.session.commit()


def add_bar_image(form_data):

    image_as_bytes = form_data.image_upload.data.read()
    file_name = form_data.item_name.data

    public_url = upload_bytes_to_gcs(bucket_name=GC_BUCKET_NAME,
                                     bytes_data=image_as_bytes,
                                     destination_blob_name=file_name)

    barcode = Barcode(
        user_id=current_user.id,
        img_public_url=public_url,
        img_gcs_path=file_name)

    db.session.add(barcode)

    db.session.commit()
def add_like(like_id):



    like = Likes(
        user_id=current_user.id,

        like_id=like_id)

    db.session.add(like)

    db.session.commit()


def add_menu(dish_title, spoon_id, day, slot):

    #dict_as_bytes = bytes(dict)
    #ile_name = file_name

    # public_url = upload_bytes_to_gcs(bucket_name=GC_BUCKET_NAME,
    # bytes_data=dict_as_bytes,
    # destination_blob_name=file_name)

    menu = Menu(dish_title=dish_title,
                spoon_id=spoon_id,
                day=day,
                slot=slot,
                user_id=current_user.id,)
    # dict_public_url=public_url,
    # dict_gcs_path=file_name)

    db.session.add(menu)

    db.session.commit()


def add_grocery(form_data, recipe_title, recipe_id):

    grocery = Food(recipe_id=recipe_id,
                   grocery_list=form_data,
                   recipe_title=recipe_title,
                   user_id=current_user.id,
                   )

    db.session.add(grocery)

    db.session.commit()


def get_products():

    df = pd.read_sql(Products.query.statement, db.session.bind)

    return df
def get_likes():

    df = pd.read_sql(Likes.query.statement, db.session.bind)

    return df
def get_users():

    df = pd.read_sql(User.query.statement, db.session.bind)

    return df

def get_grocery():

    df = pd.read_sql(Food.query.statement, db.session.bind)

    return df


def get_menu():

    df = pd.read_sql(Menu.query.statement, db.session.bind)

    return df
def get_custom():

    df = pd.read_sql(Custom.query.statement, db.session.bind)

    return df


def get_custom():

    df = pd.read_sql(Custom.query.statement, db.session.bind)

    return df
def get_fridge():

    df = pd.read_sql(Fridge.query.statement, db.session.bind)

    return df

def upload_bytes_to_gcs(bucket_name, bytes_data, destination_blob_name):

    storage_client = storage.Client()

    # get the bucket by name
    bucket = storage_client.bucket(bucket_name)

    # this creates the blob object in python but does not upload anything
    blob = bucket.blob(destination_blob_name)

    # upload the file
    blob.upload_from_string(bytes_data)

    # set the image to be publicly viewable
    blob.make_public()

    # get publicly viewable image of url
    public_img_url = blob.public_url

    return public_img_url
def write_img_to_disk(img_url, folder_prefix, filename):

    img = requests.get(img_url)

    file_path = os.path.join(folder_prefix, filename)

    with open(file_path, "wb") as file:
        file.write(img.content)

    return file_path

if __name__ == "__main__":
    app.run(debug=True)
