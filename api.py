from flask import Flask, jsonify, request, send_from_directory
from pymongo import MongoClient
from flask_socketio import SocketIO, emit, join_room
import os
from flask_cors import CORS
import google.generativeai as genai
from ddgs import DDGS
import wikipedia

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

client = MongoClient("mongodb+srv://vibeslayerdb:Apz21260%40%21@exun-goat.0bv0t4z.mongodb.net/?appName=exun-goat")
db = client.get_database('exun-goat')
users = db["users"]
reviews = db["reviews"]

genai.configure(api_key="AIzaSyCYdvCJTFFqOHHrGSDdd-DzSZOjFJbg_ss")

def get_combined_intel(query):
    print(f"-> Searching: {query}")
    context_text = ""
    sources_list = []
    
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=2):
                context_text += f"SOURCE (WEB): {r['title']} - {r['body']}\n"
                sources_list.append({"title": r['title'], "url": r['href'], "type": "web"})
    except Exception as e:
        print(f"DDG Error: {e}")
    
    try:
        search_res = wikipedia.search(query)
        if search_res:
            page = wikipedia.page(search_res[0], auto_suggest=False)
            context_text += f"SOURCE (WIKI): {page.title} - {page.summary[:300]}\n"
            sources_list.append({"title": page.title, "url": page.url, "type": "wiki"})
    except Exception as e:
        print(f"Wiki Error: {e}")
    
    if not context_text:
        context_text = "No live external data found."
    
    return context_text, sources_list

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

@app.post("/gemini_message")
def gemini_message():
    data = request.json
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(data["message"])
    return jsonify({"reply": response.text}), 200

@app.post('/api/agent_search')
def agent_search():
    data = request.json
    user_query = data.get("query")
    
    if not user_query:
        return jsonify({"error": "No query provided."}), 400
    
    print(f"--- Processing Query: {user_query} ---")
    context, sources = get_combined_intel(user_query)
    
    prompt = f"""
    User Question: {user_query}
    Context:
    {context}
    You are a micro-scale scientific assistant.
    Convert all knowledge to apply to a 1.5cm human.
    Answer in a practical, medical way. 10 sentences max.
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        print("AI Response:", response.text)
        return jsonify({
            "response": response.text,
            "sources": sources
        }), 200
    except Exception as e:
        print("🔥 AI ERROR:", str(e))
        return jsonify({"error": "Analysis Failed."}), 500

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
