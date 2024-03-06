from flask import Flask, request
import re
from redoSingleModule import redoSingleModule
from newClassSingleModule import newClassSingle

app = Flask(__name__)

@app.route('/api/redo/<guid>', methods=['GET'])
def redoClass(guid):

    guid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    if guid_regex.match(guid) is None:
        return "Invalid GUID format", 400

    try:
        response = redoSingleModule(guid, "true")
        response2 = redoSingleModule(guid, "false")
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
        response = newClassSingle(guid, "true")
        response2 = newClassSingle(guid, "false")
        response = f"{response} {response2}"
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500

if __name__ == '__main__':
    app.run()
