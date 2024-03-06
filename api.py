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
    
    staging = request.args.get('staging')
    if staging is None:
        return "Staging parameter is required", 400
    staging = staging.lower()

    try:
        response = redoSingleModule(guid, staging)
        #print("response: ", response)
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
    
@app.route('/api/new/<guid>', methods=['GET'])
def newClass(guid):

    guid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

    if guid_regex.match(guid) is None:
        return "Invalid GUID format", 400
    
    staging = request.args.get('staging')
    if staging is None:
        return "Staging parameter is required", 400
    staging = staging.lower()

    try:
        response = newClassSingle(guid, staging)
        #print("response: ", response)
        return {"message": response}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500

if __name__ == '__main__':
    app.run()
