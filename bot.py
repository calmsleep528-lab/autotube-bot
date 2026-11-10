import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import asyncio
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import moviepy.video.fx.all as vfx

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
    msg = bot.send_message(message.chat.id, "⚙️ Compiling Light-Weight Viral Video...")
    try:
        # Shortened viral script designed for 2 clips
        script_text = "Here are two weird facts that sound fake! Number one. Did you know a group of pugs is called a grumble? Imagine a grumble of dogs judging you! Number two. An octopus has three hearts, and their blood is literally blue. Hit subscribe for more!"
        asyncio.run(edge_tts.Communicate(script_text, "en-US-ChristopherNeural").save("audio.mp3"))
        audio = AudioFileClip("audio.mp3")

        # Fetch only 2 clips to safely fit inside the 512MB RAM limit
        search_terms = ["funny dog", "octopus"]
        video_clips = []
        
        for i, term in enumerate(search_terms):
            url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={term.replace(' ', '+')}&video_type=film"
            res = requests.get(url).json()
            if res['hits']:
                # CRITICAL FIX: Pulling the 'tiny' file size to save memory
                vid_url = res['hits'][0]['videos']['tiny']['url']
                vid_path = f"vid_{i}.mp4"
                with open(vid_path, "wb") as f: 
                    f.write(requests.get(vid_url).content)
                
                clip = VideoFileClip(vid_path)
                
                # CRITICAL FIX: Force aggressive resize to 640px height before processing
                clip = clip.resize(height=640)
                w, h = clip.size
                target_w = int(h * (9/16))
                
                clip = clip.fx(vfx.crop, width=target_w, height=h, x_center=w/2, y_center=h/2)
                
                # Cut each clip to exactly half the length of the audio
                clip = clip.subclip(0, min(clip.duration, audio.duration / 2))
                video_clips.append(clip)

        # Stitch the 2 clips
        final_visuals = concatenate_videoclips(video_clips, method="compose")
        final_visuals = final_visuals.set_duration(audio.duration)
        final_video = final_visuals.set_audio(audio)
        
        # Ultra-fast rendering on a single thread to prevent CPU spike
        final_video.write_videofile("final.mp4", codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=1, logger=None)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Approve & Upload", callback_data="upload"), 
                   InlineKeyboardButton("❌ Trash", callback_data="trash"))
        
        with open("final.mp4", "rb") as vid:
            bot.send_video(message.chat.id, vid, caption="Review your new Viral Short:", reply_markup=markup)
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
