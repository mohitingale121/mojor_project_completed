import pandas as pd
from pymongo import MongoClient
from urllib.parse import quote_plus

# MongoDB connection setup
username = "mohitdb"  # Replace with your MongoDB username
password = "mohitdb"  # Replace with your MongoDB password
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster.hfyt1.mongodb.net/?retryWrites=true&w=majority&appName=cluster"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client['plant_disease_db']
disease_info_collection = db['disease_info']
supplements_collection = db['supplements']

# Load disease_info.csv into pandas dataframe
disease_info = pd.read_csv('disease_info.csv', encoding='ISO-8859-1')

# Convert dataframe to dictionary and insert into MongoDB
disease_info_records = disease_info.to_dict(orient='records')
disease_info_collection.insert_many(disease_info_records)
print("Disease information inserted into MongoDB.")

# Load supplement_info.csv into pandas dataframe
supplement_info = pd.read_csv('supplement_info.csv')

# Convert dataframe to dictionary and insert into MongoDB
supplement_info_records = supplement_info.to_dict(orient='records')
supplements_collection.insert_many(supplement_info_records)
print("Supplement information inserted into MongoDB.")
