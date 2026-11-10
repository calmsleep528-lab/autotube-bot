import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import asyncio
import edge_tts
import subprocess

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY")
bot = telebot.TeleBot(BOT_TOKEN)

from flask import Flask
from threading import Thread
app = Flask(__name__)
@app.route('/')
def health_check(): return "Bot is running 24/7!"

port = int(os.environ.get("PORT", 8080))
Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "🤖 AutoTube Bot Ready.\nSend /gen to make a video.")

@bot.message_handler(commands=['gen'])
def generate(message):
    msg = bot.send_message(message.chat.id, "⚡ Compiling via Lightning FFmpeg Engine...")
    try:
        # 1. Generate Voice (Trending Fun Facts)
        script_text = "Here are two weird facts that sound completely fake! Number one. Did you know a group of pugs is called a grumble? Number two. An octopus has three hearts, and their blood is literally blue. Hit subscribe for more crazy facts!"
        asyncio.run(edge_tts.Communicate(script_text, "en-US-ChristopherNeural").save("audio.mp3"))

        # 2. Fetch 1 High-Retention "Satisfying" Background (Meta for Fact Shorts)
        url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=satisfying+slime&video_type=film"
        res = requests.get(url).json()
        vid_url = res['hits'][0]['videos']['medium']['url']
        with open("bg.mp4", "wb") as f: 
            f.write(requests.get(vid_url).content)

        # 3. Direct FFmpeg Command (20x faster than MoviePy on a free server)
        # This crops to 9:16 vertical, loops the video, stops at audio length, and merges instantly.
        ffmpeg_cmd = (
            'ffmpeg -y -stream_loop -1 -i bg.mp4 -i audio.mp3 '
            '-filter_complex "[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0[v]" '
            '-map "[v]" -map 1:a -c:v libx264 -preset ultrafast -c:a aac -shortest final.mp4'
        )
        subprocess.run(ffmpeg_cmd, shell=True, check=True)
        
        # 4. Send to Telegram
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Approve & Upload", callback_data="upload"), 
                   InlineKeyboardButton("❌ Trash", callback_data="trash"))
        
        with open("final.mp4", "rb") as vid:
            bot.send_video(message.chat.id, vid, caption="Review your Fast Viral Short:", reply_markup=markup)
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
