import os, json, sqlite3, socket, subprocess, threading, time, secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
import requests, jwt
from flask import Flask, render_template, request, jsonify, make_response, redirect
from flask_sock import Sock
from werkzeug.security import generate_password_hash, check_password_hash

BASE=os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a,**k): pass
load_dotenv(os.path.join(BASE,'.env'))
PORT=int(os.getenv('PORT','3000')); GAME_PORT=int(os.getenv('GAME_PORT','7777'))
JWT_SECRET=os.getenv('JWT_SECRET','change-me'); ADMIN_USER=os.getenv('ADMIN_USER','admin'); ADMIN_PASS=os.getenv('ADMIN_PASS','admin123')
DB_PATH=os.getenv('DB_PATH','./data/game.db')
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)),exist_ok=True)
app=Flask(__name__); sock=Sock(app)
players={}; sockets=set(); admin_sockets=set(); game_enabled=True
lock=threading.RLock()

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript('''CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, gold INTEGER DEFAULT 100, banned INTEGER DEFAULT 0, gm INTEGER DEFAULT 0, inventory TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, message TEXT, username TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);'''); c.commit()
    row=c.execute('SELECT id FROM players WHERE username=?',(ADMIN_USER,)).fetchone()
    if not row: c.execute('INSERT INTO players(username,password_hash,gm) VALUES(?,?,1)',(ADMIN_USER,generate_password_hash(ADMIN_PASS))); c.commit()
    c.close()
init_db()

def log(t,msg,u='system'):
    try:
        c=db(); c.execute('INSERT INTO logs(type,message,username) VALUES(?,?,?)',(t,msg,u)); c.commit(); c.close()
    except Exception: pass

def token_for(user): return jwt.encode({'sub':user,'exp':datetime.now(timezone.utc)+timedelta(hours=12)},JWT_SECRET,algorithm='HS256')
def auth(fn):
    @wraps(fn)
    def w(*a,**k):
        tok=request.cookies.get('admin_token') or request.headers.get('Authorization','').replace('Bearer ','')
        try: jwt.decode(tok,JWT_SECRET,algorithms=['HS256'])
        except Exception: return redirect('/login') if request.path in ['/','/panel'] else (jsonify(error='unauthorized'),401)
        return fn(*a,**k)
    return w

def lan_ip():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try: s.connect(('8.8.8.8',80)); ip=s.getsockname()[0]
    except Exception: ip='127.0.0.1'
    finally: s.close()
    return ip

def public_ip():
    try: return requests.get('https://api.ipify.org',timeout=3).text.strip()
    except Exception: return 'unavailable'

def broadcast_admin(payload):
    dead=[]
    with lock:
        for ws in list(admin_sockets):
            try: ws.send(json.dumps(payload))
            except Exception: dead.append(ws)
        for ws in dead: admin_sockets.discard(ws)

def save_player(username,**fields):
    if not fields:return
    sets=[]; vals=[]
    for k,v in fields.items(): sets.append(k+'=?'); vals.append(v)
    vals += [datetime.utcnow().isoformat(),username]
    c=db(); c.execute(f'UPDATE players SET {", ".join(sets)}, updated_at=? WHERE username=?',vals); c.commit(); c.close()

@app.get('/login')
def login(): return render_template('login.html')
@app.post('/api/admin/login')
def admin_login():
    d=request.get_json() or {}; u=d.get('username',''); p=d.get('password','')
    if u!=ADMIN_USER or p!=ADMIN_PASS: return jsonify(error='Sai tài khoản hoặc mật khẩu'),401
    r=make_response(jsonify(ok=True)); r.set_cookie('admin_token',token_for(u),httponly=True,samesite='Lax',max_age=43200); log('admin','Admin đăng nhập',u); return r
@app.get('/')
@auth
def home(): return render_template('panel.html')
@app.get('/panel')
@auth
def panel(): return render_template('panel.html')
@app.post('/api/logout')
@auth
def logout(): r=make_response(jsonify(ok=True)); r.delete_cookie('admin_token'); return r
@app.get('/api/status')
@auth
def status(): return jsonify(lan_ip=lan_ip(),public_ip=public_ip(),game_port=GAME_PORT,admin_port=PORT,online=len(players),game_enabled=game_enabled)
@app.get('/api/players')
@auth
def get_players():
    c=db(); rows=[dict(x) for x in c.execute('SELECT id,username,level,exp,gold,banned,gm,created_at,updated_at FROM players ORDER BY id DESC')]; c.close();
    for x in rows: x['online']=x['username'] in players
    return jsonify(rows)
@app.post('/api/players')
@auth
def create_player():
    d=request.get_json() or {}; u=d.get('username','').strip(); p=d.get('password','')
    if len(u)<3 or len(p)<4:return jsonify(error='Username >=3, password >=4'),400
    try:
        c=db(); c.execute('INSERT INTO players(username,password_hash) VALUES(?,?)',(u,generate_password_hash(p))); c.commit(); c.close(); log('account','Tạo player '+u); return jsonify(ok=True)
    except sqlite3.IntegrityError:return jsonify(error='Username đã tồn tại'),409
@app.delete('/api/players/<username>')
@auth
def delete_player(username):
    c=db(); c.execute('DELETE FROM players WHERE username=?',(username,)); c.commit(); c.close(); log('account','Xoá player '+username); return jsonify(ok=True)
@app.post('/api/players/<username>/ban')
@auth
def ban_player(username): d=request.get_json() or {}; b=1 if d.get('banned',True) else 0; save_player(username,banned=b); log('moderation',f'ban={b} {username}'); return jsonify(ok=True)
@app.post('/api/players/<username>/gm')
@auth
def gm_player(username): d=request.get_json() or {}; save_player(username,gm=1 if d.get('gm') else 0); return jsonify(ok=True)
@app.post('/api/players/<username>/password')
@auth
def reset_password(username):
    d=request.get_json() or {}; p=d.get('password','')
    if len(p)<4:return jsonify(error='Password quá ngắn'),400
    save_player(username,password_hash=generate_password_hash(p)); log('account','Reset mật khẩu '+username); return jsonify(ok=True)
@app.post('/api/players/<username>/grant')
@auth
def grant(username):
    d=request.get_json() or {}; gold=int(d.get('gold',0)); exp=int(d.get('exp',0)); item=d.get('item','').strip()
    c=db(); row=c.execute('SELECT gold,exp,inventory FROM players WHERE username=?',(username,)).fetchone()
    if not row:return jsonify(error='Không tồn tại'),404
    inv=json.loads(row['inventory'] or '{}');
    if item: inv[item]=int(inv.get(item,0))+1
    c.execute('UPDATE players SET gold=?,exp=?,inventory=?,updated_at=CURRENT_TIMESTAMP WHERE username=?',(row['gold']+gold,row['exp']+exp,json.dumps(inv),username)); c.commit(); c.close()
    if username in players: players[username]['gold']+=gold; players[username]['exp']+=exp; players[username]['inventory']=inv
    log('grant',f'gold={gold} exp={exp} item={item}',username); broadcast_admin({'type':'players','online':list(players.values())}); return jsonify(ok=True)
@app.get('/api/logs')
@auth
def logs():
    c=db(); rows=[dict(x) for x in c.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 200')]; c.close(); return jsonify(rows)
@app.post('/api/backup')
@auth
def backup():
    path=DB_PATH+'.backup'; src=sqlite3.connect(DB_PATH); dst=sqlite3.connect(path); src.backup(dst); dst.close(); src.close(); log('backup','Database backup '+path); return jsonify(ok=True,path=path)
@app.post('/api/game/<action>')
@auth
def game_action(action):
    global game_enabled
    if action=='stop': game_enabled=False
    elif action in ('start','restart'): game_enabled=True
    else:return jsonify(error='action'),400
    for ws in list(sockets):
        try: ws.send(json.dumps({'type':'server','enabled':game_enabled}))
        except Exception: pass
    log('server',action); return jsonify(ok=True,enabled=game_enabled)

@app.post('/api/login')
def player_login():
    d=request.get_json() or {}; u=d.get('username',''); p=d.get('password','')
    c=db(); row=c.execute('SELECT * FROM players WHERE username=?',(u,)).fetchone(); c.close()
    if not row or row['banned'] or not check_password_hash(row['password_hash'],p): return jsonify(error='Đăng nhập thất bại'),401
    return jsonify(token=token_for(u),username=u,level=row['level'],exp=row['exp'],gold=row['gold'],inventory=json.loads(row['inventory'] or '{}'))
@app.post('/api/register')
def register():
    d=request.get_json() or {}; u=d.get('username','').strip(); p=d.get('password','')
    if len(u)<3 or len(p)<4:return jsonify(error='Username >=3, password >=4'),400
    try:
        c=db(); c.execute('INSERT INTO players(username,password_hash) VALUES(?,?)',(u,generate_password_hash(p))); c.commit(); c.close(); log('account','Đăng ký '+u); return jsonify(ok=True)
    except sqlite3.IntegrityError:return jsonify(error='Username đã tồn tại'),409

@sock.route('/game')
def game_ws(ws):
    global game_enabled
    username=None
    try:
        raw=ws.receive(); d=json.loads(raw or '{}')
        if d.get('type')!='auth': ws.send(json.dumps({'type':'error','message':'auth required'})); return
        try: username=jwt.decode(d.get('token',''),JWT_SECRET,algorithms=['HS256'])['sub']
        except Exception: ws.send(json.dumps({'type':'error','message':'token invalid'})); return
        if not game_enabled: ws.send(json.dumps({'type':'error','message':'server stopped'})); return
        c=db(); row=c.execute('SELECT * FROM players WHERE username=?',(username,)).fetchone(); c.close()
        if not row or row['banned']: return
        with lock: sockets.add(ws); players[username]={'username':username,'x':120+len(players)*45,'y':280,'level':row['level'],'exp':row['exp'],'gold':row['gold'],'inventory':json.loads(row['inventory'] or '{}')}
        broadcast_admin({'type':'online','online':list(players.values())})
        ws.send(json.dumps({'type':'state','players':list(players.values())}))
        while True:
            raw=ws.receive()
            if raw is None: break
            d=json.loads(raw)
            if d.get('type')=='move':
                p=players[username]; p['x']=max(32,min(1960,p['x']+float(d.get('dx',0)))); p['y']=max(120,min(600,p['y']+float(d.get('dy',0))))
            elif d.get('type')=='attack':
                log('combat',username+' attack',username)
            elif d.get('type')=='chat':
                msg=str(d.get('message',''))[:200]; log('chat',msg,username)
            elif d.get('type')=='save':
                p=players[username]; save_player(username,level=p['level'],exp=p['exp'],gold=p['gold'],inventory=json.dumps(p['inventory']))
            ws.send(json.dumps({'type':'state','players':list(players.values())}))
    except Exception: pass
    finally:
        if username:
            with lock: sockets.discard(ws); players.pop(username,None)
            broadcast_admin({'type':'online','online':list(players.values())})

@sock.route('/admin-ws')
@auth
def admin_ws(ws):
    admin_sockets.add(ws)
    try:
        ws.send(json.dumps({'type':'online','online':list(players.values())}))
        while True:
            if ws.receive() is None: break
    except Exception: pass
    finally: admin_sockets.discard(ws)

if __name__=='__main__':
    print(f'Admin: http://0.0.0.0:{PORT} | Game WS: ws://0.0.0.0:{GAME_PORT}/game')
    # Flask-Sock uses one HTTP server, so expose game WS on GAME_PORT through a second process below.
    # For a single-process deployment, both ports are served by the same app only if launched twice.
    # Default entrypoint starts two processes.
