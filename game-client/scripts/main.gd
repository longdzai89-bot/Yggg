extends Node2D
var mode="login"; var server_ip="127.0.0.1"; var server_port=7777; var token=""; var username=""; var players={}; var connected=false; var msg=""
var me={"x":160.0,"y":330.0,"level":1,"gold":100,"exp":0,"inventory":{}}
var http:HTTPRequest; var ws=WebSocketPeer.new(); var name_edit:LineEdit; var pass_edit:LineEdit; var ip_edit:LineEdit
var mobs=[{"x":600.0,"y":340.0,"hp":80,"name":"Sói"},{"x":800.0,"y":300.0,"hp":140,"name":"Gấu"},{"x":1050.0,"y":360.0,"hp":220,"name":"Raptor"}]
func _ready():
 http=HTTPRequest.new(); add_child(http); _build_login_ui(); queue_redraw()
func _build_login_ui():
 name_edit=LineEdit.new(); pass_edit=LineEdit.new(); ip_edit=LineEdit.new(); name_edit.placeholder_text="Tên tài khoản"; pass_edit.placeholder_text="Mật khẩu"; ip_edit.placeholder_text="IP server"; pass_edit.secret=true
 name_edit.position=Vector2(350,255); pass_edit.position=Vector2(350,305); ip_edit.position=Vector2(350,355); ip_edit.text=server_ip
 for e in [name_edit,pass_edit,ip_edit]: e.size=Vector2(260,40); e.add_theme_font_size_override("font_size",16); add_child(e)
 var b=Button.new(); b.text="ĐĂNG NHẬP"; b.position=Vector2(350,410); b.size=Vector2(125,45); b.pressed.connect(do_login); add_child(b)
 var r=Button.new(); r.text="ĐĂNG KÝ"; r.position=Vector2(485,410); r.size=Vector2(125,45); r.pressed.connect(do_register); add_child(r)
func _process(delta):
 if mode=="game": _poll_ws(); _move(delta)
 queue_redraw()
func _move(delta):
 var v=Input.get_vector("ui_left","ui_right","ui_up","ui_down")
 if v.length()>0.0:
  me.x=clamp(me.x+v.x*180.0*delta,30.0,1900.0); me.y=clamp(me.y+v.y*180.0*delta,180.0,470.0)
  if connected: ws.send_text(JSON.stringify({"type":"move","dx":v.x*180.0*delta,"dy":v.y*180.0*delta}))
func _post(path:String,body:Dictionary):
 server_ip=ip_edit.text.strip_edges(); http.request("http://"+server_ip+":3000"+path,["Content-Type: application/json"],HTTPClient.METHOD_POST,JSON.stringify(body))
func do_login():
 msg="Đang đăng nhập..."; _post("/api/login",{"username":name_edit.text.strip_edges(),"password":pass_edit.text}); await http.request_completed
 var d=JSON.parse_string(http.get_body_as_string())
 if typeof(d)==TYPE_DICTIONARY and d.has("token"): username=name_edit.text.strip_edges(); token=d.token; me.level=d.level; me.gold=d.gold; me.exp=d.exp; me.inventory=d.inventory; _enter_game()
 else: msg=(str(d.get("error","Login failed")) if typeof(d)==TYPE_DICTIONARY else "Server error")
func do_register():
 msg="Đang đăng ký..."; _post("/api/register",{"username":name_edit.text.strip_edges(),"password":pass_edit.text}); await http.request_completed
 var d=JSON.parse_string(http.get_body_as_string()); msg=("Đăng ký thành công — hãy đăng nhập" if typeof(d)==TYPE_DICTIONARY and d.get("ok",false) else str(d.get("error","Lỗi")))
func _enter_game():
 for n in [name_edit,pass_edit,ip_edit]: n.hide()
 for child in get_children():
  if child is Button: child.hide()
 ws=WebSocketPeer.new(); var err=ws.connect_to_url("ws://"+server_ip+":"+str(server_port)+"/game")
 if err!=OK: msg="Không kết nối được game server"; return
 mode="game"; await get_tree().create_timer(0.25).timeout; ws.send_text(JSON.stringify({"type":"auth","token":token}))
func _poll_ws():
 ws.poll()
 if ws.get_ready_state()==WebSocketPeer.STATE_OPEN:
  connected=true
  while ws.get_available_packet_count()>0:
   var d=JSON.parse_string(ws.get_packet().get_string_from_utf8())
   if typeof(d)==TYPE_DICTIONARY:
    if d.get("type")=="state":
     for p in d.get("players",[]): players[p.username]=p
    elif d.get("type")=="error": msg=str(d.message)
 else: connected=false
func _input(e):
 if mode=="game" and e is InputEventMouseButton and e.pressed and Rect2(750,460,150,45).has_point(e.position):
  if connected: ws.send_text(JSON.stringify({"type":"attack"}))
func _draw():
 draw_rect(Rect2(0,0,2200,700),Color("101812")); _draw_login() if mode=="login" else _draw_game()
func _draw_login():
 draw_string(ThemeDB.fallback_font,Vector2(330,110),"PRIMITIVE REALM",0,500,42,Color("d7b56d")); draw_string(ThemeDB.fallback_font,Vector2(350,145),"STONE AGE ONLINE",0,400,18,Color("a5ad9a")); draw_rect(Rect2(330,190,320,300),Color("181e18")); draw_rect(Rect2(330,190,320,300),Color("394537"),false,2); draw_string(ThemeDB.fallback_font,Vector2(350,225),"Đăng nhập / Đăng ký",0,-1,18,Color.WHITE); draw_string(ThemeDB.fallback_font,Vector2(350,510),msg,0,500,15,Color("d9a45f"))
func _draw_game():
 draw_rect(Rect2(0,430,2200,270),Color("263a25")); draw_rect(Rect2(0,0,2200,120),Color("17251c"))
 for x in range(0,2200,90): draw_circle(Vector2(x+25,405),35,Color("345431")); draw_rect(Rect2(x+20,400,10,55),Color("493523"))
 for m in mobs: _mob(Vector2(m.x,m.y),m.name,m.hp)
 _player(Vector2(me.x,me.y),username)
 for k in players.keys():
  var p=players[k]
  if k!=username: _player(Vector2(p.x,p.y),k)
 draw_rect(Rect2(15,15,340,85),Color("111712")); draw_string(ThemeDB.fallback_font,Vector2(30,45),username+"  Lv."+str(me.level),0,-1,20,Color.WHITE); draw_string(ThemeDB.fallback_font,Vector2(30,72),"HP 100   EXP "+str(me.exp)+"   Gold "+str(me.gold),0,-1,16,Color("d8c37a")); draw_rect(Rect2(720,390,220,130),Color("111712")); draw_string(ThemeDB.fallback_font,Vector2(740,420),"BÀN PHÍM",0,-1,16,Color("d8c37a")); draw_string(ThemeDB.fallback_font,Vector2(740,447),"← → ↑ ↓  Di chuyển",0,-1,15,Color.WHITE); draw_rect(Rect2(750,460,150,45),Color("394b36")); draw_string(ThemeDB.fallback_font,Vector2(770,489),"TẤN CÔNG",0,-1,16,Color.WHITE); draw_string(ThemeDB.fallback_font,Vector2(20,520),"4 hướng • cận chiến • thú AI prototype • multiplayer WebSocket",0,-1,15,Color("aab3a5")); draw_string(ThemeDB.fallback_font,Vector2(20,550),msg,0,-1,15,Color("d9a45f"))
func _player(pos:Vector2,n:String): draw_circle(pos,18,Color("C19A6B")); draw_rect(Rect2(pos.x-14,pos.y+14,28,24),Color("3B2A1A")); draw_line(pos+Vector2(13,8),pos+Vector2(32,-12),Color("7A6A55"),5); draw_string(ThemeDB.fallback_font,pos+Vector2(-35,-28),n,0,90,12,Color.WHITE)
func _mob(pos:Vector2,n:String,hp:int): draw_circle(pos,23,Color("6c604d")); draw_circle(pos+Vector2(0,-14),17,Color("4d4638")); draw_circle(pos+Vector2(-6,-17),3,Color("d55d45")); draw_circle(pos+Vector2(6,-17),3,Color("d55d45")); draw_string(ThemeDB.fallback_font,pos+Vector2(-25,-36),n,0,100,13,Color("e0c58c")); draw_rect(Rect2(pos.x-25,pos.y+28,50,5),Color("542525")); draw_rect(Rect2(pos.x-25,pos.y+28,50*hp/220.0,5),Color("9b5145"))
