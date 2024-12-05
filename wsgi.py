from gevent import monkey
monkey.patch_all()

from api import app
from api import socketio

if __name__ == "__main__":
    socketio.run(app)