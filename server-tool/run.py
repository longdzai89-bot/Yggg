import os, subprocess, sys
from app import app, sock, PORT, GAME_PORT
# The same Flask app exposes both WebSocket routes; run two WSGI instances on separate ports.
if __name__=='__main__':
    role=os.getenv('SERVER_ROLE','admin')
    port=GAME_PORT if role=='game' else PORT
    app.run(host='0.0.0.0',port=port,threaded=True)
