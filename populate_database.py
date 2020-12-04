
from main import db, GC_BUCKET_NAME, upload_bytes_to_gcs, automl, Products, User
from google.cloud import storage
import spoonacular as sp
from google.cloud import automl_v1beta1
from google.cloud import language_v1
import string
import random
from flask_bcrypt import Bcrypt
import pandas as pd
bcrypt = Bcrypt()
import requests
import json
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./gcp_credentials/astral-charter-294311-a6531ff12b3e.json"
db.session.rollback()
from secrets import SQL_PASSWORD, SQL_PUBLIC_IP, SQL_DATABASE_NAME, FOODREPO_KEY , SPOON_KEY ,PROJECT_ID,MODEL_ID, BUCKET_NAME ,SECRET_KEY

API_KEY=SPOON_KEY
dish="bread"
content = requests.get(
    "https://api.spoonacular.com/recipes/findByIngredients?ingredients=" +
    dish +
    "&apiKey=" + API_KEY)
json_response = json.loads(content.text)
list1=[]
for n in json_response:
    if n['id'] > 0:
        list1.append(n['id'])




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

def add_product(title, time, recipe, img):

    image_as_bytes = img
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
                       user_id= 1,
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


user1 = User(name="Eric3",
             email="eric3.master@unisg.ch",
             password= bcrypt.generate_password_hash("123456"))

db.session.add(user1)


db.session.commit()

for n in list1:
    response = requests.get("https://api.spoonacular.com/recipes/informationBulk?ids=" +
                            str(n)+"&includeNutrition=true&apiKey="+API_KEY)

    response2 = json.loads(response.text)
    import random
    time = random.randint(10,80)
    url= response2[0]['image']
    img = requests.get(url).content
    #img = Image.open(BytesIO(response.content))

    recipe=response2[0]['instructions']
    if recipe == None:
        recipe=response2[0]['title']

    recipe_title = response2[0]['title']

    add_product(recipe_title,time, recipe, img)
