import pyrebase
import json


def get_firebase_ref():
    fb = None

    # load credentials from json file
    with open('./credentials/firebase.json', 'r') as f:
        fb = json.load(f)

    firebase = pyrebase.initialize_app(fb['CONFIG'])
    auth = firebase.auth()

    # Log the user in
    user = auth.sign_in_with_email_and_password(
        fb['USER_EMAIL'], fb['USER_PASSWORD'])

    return (user, firebase.database())
