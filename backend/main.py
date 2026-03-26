import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

# --- 1. SET UP THE VAULT (DATABASE) ---
conn = sqlite3.connect('patients.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        age TEXT,
        weight TEXT,
        sex TEXT,
        patient_message TEXT,
        ai_reply TEXT
    )
''')
conn.commit()

# --- 2. SET UP THE AI ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')
chat_session = model.start_chat(history=[])

# --- 3. SET UP THE SERVER ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. DATA BLUEPRINTS ---
class ProfileRequest(BaseModel):
    age: str
    weight: str
    sex: str

class ChatRequest(BaseModel):
    message: str
    patient_profile: ProfileRequest 

@app.post("/chat")
async def chat(request: ChatRequest):
    context_prompt = f"[Patient Profile: {request.patient_profile.age} years old, {request.patient_profile.weight}kg, {request.patient_profile.sex}]. They say: {request.message}"
    
    try:
        # Try to ask Google
        response = chat_session.send_message(context_prompt)
        reply_text = response.text
        
        # Only save to database if Google actually answered!
        cursor.execute('''
            INSERT INTO consultations (age, weight, sex, patient_message, ai_reply)
            VALUES (?, ?, ?, ?, ?)
        ''', (request.patient_profile.age, request.patient_profile.weight, request.patient_profile.sex, request.message, reply_text))
        conn.commit()
        
    except Exception as e:
        # If Google blocks us or throws an error, reply nicely instead of crashing!
        print(f"DEBUG ERROR: {type(e).__name__} - {str(e)}")
        reply_text = "I am receiving too many requests right now! Please wait about 60 seconds and try again."

    return {"reply": reply_text}