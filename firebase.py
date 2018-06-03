import pyrebase

config = {
    "apiKey": "AIzaSyDdFNeEvjtNKINuXmiS1iruAxbPPb3Zkng",
    "authDomain": "droneium-gix.firebaseapp.com",
    "databaseURL": "https://droneium-gix.firebaseio.com",
    "projectId": "droneium-gix",
    "storageBucket": "droneium-gix.appspot.com",
    "messagingSenderId": "372779620949"
}


def get_firebase_ref():
    firebase = pyrebase.initialize_app(config)
    return firebase.database()
