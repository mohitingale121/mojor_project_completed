from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
from urllib.parse import quote_plus
import tensorflow as tf
import numpy as np
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
import time

# Flask app initialization
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection setup
username = "mohitdb"  # Replace with your MongoDB username
password = "mohitdb"  # Replace with your MongoDB password
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

# MongoDB URI and client
MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster.hfyt1.mongodb.net/plant_disease_db?retryWrites=true&w=majority"

# Initialize MongoDB client and database connection
client = None
db = None
registrations_collection = None
supplements_collection = None

# Retry logic for MongoDB connection
def connect_to_mongo():
    global client, db, registrations_collection, supplements_collection
    retries = 5  # Number of retry attempts
    for attempt in range(retries):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client['plant_disease_db']  # Database name
            registrations_collection = db['registrations']
            supplements_collection = db['supplements']
            print("MongoDB connection successful.")
            return True
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            if attempt < retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Failed to connect to MongoDB after multiple attempts.")
                return False

# Attempt MongoDB connection
if not connect_to_mongo():
    print("MongoDB connection failed. Please check your MongoDB setup.")

# Paths for model, disease info, and supplement info
MODEL_PATH = "trained_plant_disease_model.keras"
DISEASE_INFO_PATH = "disease_info.csv"
SUPPLEMENT_INFO_PATH = "supplement_info.csv"

# Load model and CSV data
model = tf.keras.models.load_model(MODEL_PATH)
disease_info = pd.read_csv(DISEASE_INFO_PATH, encoding='ISO-8859-1')
supplement_info = pd.read_csv(SUPPLEMENT_INFO_PATH)

# Class names for disease prediction
class_names = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Blueberry___healthy', 'Cherry___Powdery_mildew',
    'Cherry___healthy', 'Corn___Cercospora_leaf_spot Gray_leaf_spot',
    'Corn___Common_rust', 'Corn___Northern_Leaf_Blight', 'Corn___healthy',
    'Grape___Black_rot', 'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
    'Grape___healthy', 'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot',
    'Peach___healthy', 'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy',
    'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
    'Raspberry___healthy', 'Soybean___healthy', 'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch', 'Strawberry___healthy', 'Tomato___Bacterial_spot',
    'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold',
    'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite',
    'Tomato___Target_Spot', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus',
    'Tomato___healthy'
]

# Model prediction
def model_prediction(test_image):
    from tensorflow.keras.preprocessing import image
    img = image.load_img(test_image, target_size=(128, 128))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # Convert image to batch
    prediction = model.predict(img_array)
    return np.argmax(prediction)

# Save registration and prediction data to MongoDB
def save_registration_data(form_data, disease_name, city_name):
    try:
        registration_data = {
            "name": form_data['name'],
            "email": form_data['email'],
            "city": city_name,
            "gender": form_data['gender'],
            "country": form_data['country'],
            "message": form_data['message'],
            "disease_name": disease_name,
            "timestamp": datetime.now()
        }
        registrations_collection.insert_one(registration_data)
        print("Registration data saved successfully.")
    except Exception as e:
        print(f"Error inserting into MongoDB: {e}")

# Get disease and supplement details
def get_disease_info(disease_name):
    disease_rows = disease_info[disease_info['disease_name'] == disease_name]
    if not disease_rows.empty:
        disease_description = disease_rows['description'].values[0]
        possible_steps = disease_rows['Possible Steps'].values[0]
        image_url = disease_rows['image_url'].values[0]
    else:
        disease_description = "Description not available."
        possible_steps = "No steps available."
        image_url = None

    supplements = list(supplements_collection.find({"Disease": disease_name}))
    return disease_description, possible_steps, image_url, supplements

# Routes
@app.route('/')
def home():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    form_data = {
        "name": request.form.get('name'),
        "email": request.form.get('email'),
        "city": request.form.get('city'),
        "gender": request.form.get('gender'),
        "country": request.form.get('country'),
        "message": request.form.get('message')
    }
    session['form_data'] = form_data  # Store form data in session
    return redirect(url_for('index'))

@app.route('/index')
def index():
    form_data = session.get('form_data')  # Retrieve form data from session
    return render_template('index.html', form_data=form_data)

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join('uploads', filename)
    file.save(file_path)

    # Predict disease
    result_index = model_prediction(file_path)
    disease_name = class_names[result_index]

    # Save to MongoDB
    form_data = session.get('form_data')
    save_registration_data(form_data, disease_name, form_data['city'])

    # Get disease info
    disease_description, possible_steps, image_url, supplements = get_disease_info(disease_name)

    return render_template('result.html', disease_name=disease_name, description=disease_description,
                           steps=possible_steps, image_url=image_url, supplements=supplements)

if __name__ == "__main__":
    app.run(debug=True)
