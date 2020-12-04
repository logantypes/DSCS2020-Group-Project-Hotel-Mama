from main import db, GC_BUCKET_NAME, Products
from google.cloud import storage


db.drop_all()
db.create_all()
db.session.commit()
# create bucket
storage_client = storage.Client()
storage_client.create_bucket(GC_BUCKET_NAME)


import pandas as pd
from sqlalchemy import create_engine

from secrets import SQL_PASSWORD, SQL_PUBLIC_IP, SQL_DATABASE_NAME, FOODREPO_KEY , SPOON_KEY ,PROJECT_ID,MODEL_ID, BUCKET_NAME ,SECRET_KEY

# Google Cloud SQL settings
PASSWORD = SQL_PASSWORD
PUBLIC_IP_ADDRESS = SQL_PUBLIC_IP
DBNAME = SQL_DATABASE_NAME

# set up the engine connecting us with the database
connection_string = f"postgresql://postgres:{PASSWORD}@{PUBLIC_IP_ADDRESS}/{DBNAME}"
engine = create_engine(connection_string)
query1 = """

DROP  TABLE if exists "user" cascade;
"""
query2 = """

DROP  TABLE if exists "products" cascade;
"""
engine.execute(query1)
engine.execute(query2)


# as completely deleting your database - which is an extreme way of resolving
# an error anyways - is no longer an option, you can instead resort to the
# drop_all() command if necessary
#
# db.drop_all()


# Delete bucket: Run this code to delete bucket from cloud storage. Note that
# while bucket is deleted, the files are not yet fully erased yet. Google holds
# on to the files in a bin and only deletes them after ~30 days. Images are not
# automatically overwritten and public urls will remain accessible until the
# files are fully deleted
#
# storage_client = storage.Client()
# bucket = storage_client.bucket(GC_BUCKET_NAME)
# bucket.delete(force=True)
