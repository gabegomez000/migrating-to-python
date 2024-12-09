from flask import Flask, request, render_template, redirect, url_for, Response
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
import re, sys
import requests
from dotenv import dotenv_values
from redoSingleModule import redoSingleModule
from newClassSingleModule import newClassSingle
from newMeetSingleModule import newMeetSingle

config = dotenv_values(".env")

class RealTimeEmiter:
    def __init__(self, socketio, event_name):
        self.socketio = socketio
        self.event_name = event_name

    def write(self, message):
        self.socketio.emit(self.event_name, {"output": message.strip()})

    def flush(self):
        pass

app = Flask(__name__)
app.config['SECRET_KEY'] = config['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Optional, to suppress a warning
db = SQLAlchemy(app)
socketio = SocketIO(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route("/", methods=["GET", "POST"])
@login_required
def form():
    return render_template("form_with_output.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        # Replace with actual authentication logic
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/")
        else:
            return Response('Invalid credentials', 401)
    return render_template("login.html")

@app.route('/api/redo/<guid>', methods=['GET'])
def redoClass(guid):

    guid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    if guid_regex.match(guid) is None:
        return "Invalid GUID format", 400

    try:
        response = redoSingleModule(guid, True)
        response2 = redoSingleModule(guid, False)
        response = f"{response} {response2}"
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
    
@app.route('/api/new/<guid>', methods=['GET'])
def newClass(guid):

    guid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    if guid_regex.match(guid) is None:
        return "Invalid GUID format", 400

    try:
        response = newClassSingle(guid, True)
        response2 = newClassSingle(guid, False)
        response = f"{response} {response2}"
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
    
@app.route('/api/new/meeting/<guid>', methods=['POST'])
def newMeeting(guid):

    guid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    if guid_regex.match(guid) is None:
        return "Invalid GUID format", 400

    try:
        response = newMeetSingle(guid, True)
        response2 = newMeetSingle(guid, False)
        response = f"{response} {response2}"
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
    
@socketio.on("submit_form")
def handle_form(data):
    # Extract data from the received event
    class_url = data.get("class_url")

    # Regular expression to match GUIDs
    guid_pattern = r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"

    # Search for the GUID in the text
    match = re.search(guid_pattern, class_url)
    if match is None:
        emit("update_output", {"output": "Could not find GUID in URL!"})
    else:
        guid = match.group(0)

        # Redirect stdout to capture print statements
        old_stdout = sys.stdout
        sys.stdout = RealTimeEmiter(socketio, "update_output")

        try:
            emit("update_output", {"output": "Checking if page exists..."})
            response = requests.get(f"{config['WORDPRESS_URL']}/events/by-slug/{guid}")
            #emit("update_output", {"output": f"Response code: {response.status_code}"})
            if response.status_code == 200:
                emit("update_output", {"output": "Page exists!"})
                emit("update_output", {"output": "Starting update process..."})
                redoSingleModule(guid, True)
                redoSingleModule(guid, False)
            else:
                emit("update_output", {"output": f"Page not found!"})
                emit("update_output", {"output": "Starting creation process..."})
                newClassSingle(guid, True)
                newClassSingle(guid, False)
        except requests.RequestException as e:
            emit("update_output", {"output": f"An error occurred: {str(e)}"})            
        finally:
            sys.stdout = old_stdout
        
        # Signal process completion
        emit("update_output", {"output": "All done!"})

if __name__ == '__main__':
    socketio.run(app)
