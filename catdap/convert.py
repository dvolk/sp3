import yaml
import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["catdap"]
accounts_db = mydb["accounts"]
organisations_db = mydb["organisations"]
tokens_db = mydb["tokens"]

with open("config.yaml") as f:
    state = yaml.load(f.read())

for org_name, vals in state["organisations"].items():
    vals["name"] = org_name
    organisations_db.insert_one( vals )

for username, vals in state["users"].items():
    vals["username"] = username
    accounts_db.insert_one( vals )
