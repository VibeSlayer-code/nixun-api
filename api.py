from flask import Flask, jsonify, request, send_from_directory
from pymongo import MongoClient
from flask_socketio import SocketIO, emit, join_room
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")  # <-- Add this line


client = MongoClient("mongodb+srv://vibeslayerdb:Apz21260%40%21@exun-goat.0bv0t4z.mongodb.net/?appName=exun-goat")
db = client.get_database('exun-goat')
users = db["users"]
reviews = db["reviews"]


@app.post("/add_user")
def add_user():
    data = request.json
    users.insert_one(data)
    data.pop("_id", None)
    return jsonify({"status": "OK", "message": "[+] user add success", "data": data}), 201

@app.post("/check_user")
def check_user():
    data = request.json
    user = users.find_one({"email": data["email"]})
    if not user:
        return jsonify({"status": "bad", "message": "[-] user not found"}), 404
    
    user.pop("_id", None)
    if user["password"] == data["password"]:
        return jsonify({"status": "OK", "message": "[+] user logged in success", "data": user}), 200
    
    return jsonify({"status": "bad", "message": "[-] incorrect password"}), 401



@app.post("/send_review")
def send_review():
    data = request.json
    reviews.insert_one(data)
    data.pop("_id", None)
    return jsonify({"status": "OK", "message": "[+] review added success", "data": data}), 201

@app.get("/view_review")
def view_review():
    all_reviews = list(reviews.find({}, {"_id": 0}))
    return jsonify({
        "status": "OK",
        "message": "[+] reviews fetched success",
        "data": all_reviews
    }), 200



# Serve index.html at root
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return "", 404



@socketio.on("connect")
def handle_connect():
    print(f"[+] Client connected: {request.sid}")
    emit("connected", {"message": "Connected to server"})

@socketio.on("disconnect")
def handle_disconnect():
    print(f"[-] Client disconnected: {request.sid}")

@socketio.on("join")
def join(data):
    room = data["room"]
    join_room(room)
    print(f"[+] {request.sid} joined room: {room}")
    emit("user-joined", {"room": room, "userId": request.sid}, room=room, include_self=False)

@socketio.on("offer")
def offer(data):
    room = data["room"]
    emit("offer", {"offer": data["offer"]}, room=room, include_self=False)

@socketio.on("answer")
def answer(data):
    room = data["room"]
    emit("answer", {"answer": data["answer"]}, room=room, include_self=False)

@socketio.on("ice")
def ice(data):
    room = data["room"]
    emit("ice", {"candidate": data["candidate"]}, room=room, include_self=False)



if __name__ == "__main__":
    print("\n" + "="*60)
    print(" FLASK SERVER STARTED ".center(60, "="))
    print(" Visit → http://127.0.0.1:5000 ".center(60))
    print("="*60 + "\n")
    

    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule} → {rule.endpoint}")
    print()

    socketio.run(app, debug=True, host="0.0.0.0", port=5000)