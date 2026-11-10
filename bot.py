import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import asyncio
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip
import moviepy.video.fx.all as vfx

# API Keys from Render Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY")
bot = telebot.TeleBot(BOT_TOKEN)

# Dummy web server to keep Render awake (Updated Port Fix)
from flask import Flask
from threading import Thread
app = Flask(__name__)
@app.route('/')
def health_check(): return "Bot is running 24/7!"

# This line grabs the dynamic port Render requires, instead of forcing 8080
port = int(os.environ.get("PORT", 8080))
Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "🤖 AutoTube Bot Ready.\nSend /gen to make a video.")

@bot.message_handler(commands=['gen'])
def generate(message):
    msg = bot.send_message(message.chat.id, "⚙️ Compiling video on cloud server... (takes ~1 min)")
    try:
        # 1. Generate Voice
        script_text = "Did you know that your brain uses 20 percent of your body's energy, even though it only makes up 2 percent of your weight?"
        asyncio.run(edge_tts.Communicate(script_text, "en-US-ChristopherNeural").save("audio.mp3"))
        
        # 2. Fetch Video
        url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=medicine&video_type=film&orientation=vertical"
        vid_url = requests.get(url).json()['hits'][0]['videos']['medium']['url']
        with open("bg.mp4", "wb") as f: 
            f.write(requests.get(vid_url).content)
        
        # 3. Merge Audio & Video
        audio = AudioFileClip("audio.mp3")
        video = VideoFileClip("bg.mp4").fx(vfx.loop, duration=audio.duration)
        final_video = video.set_audio(audio)
        final_video.write_videofile("final.mp4", codec="libx264", audio_codec="aac", fps=30, preset="ultrafast", logger=None)
        
        # 4. Send to Telegram with Trading Bot Buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Approve & Upload", callback_data="upload"), 
                   InlineKeyboardButton("❌ Trash", callback_data="trash"))
        
        with open("final.mp4", "rb") as vid:
            bot.send_video(message.chat.id, vid, caption="Review your new Short:", reply_markup=markup)
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"Error: {e}", message.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "upload":
        bot.answer_callback_query(call.id, "Uploading to YouTube API (Module Next!)")
        bot.edit_message_caption("✅ *Approved & Scheduled for Upload*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    elif call.data == "trash":
        bot.answer_callback_query(call.id, "Trashed.")
        bot.delete_message(call.message.chat.id, call.message.message_id)

bot.polling(non_stop=True)
