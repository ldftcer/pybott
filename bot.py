from pyrogram import Client, filters
import yt_dlp
import os
import subprocess
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = '7246695508:AAFynFXANrHO-JoQw1Sxdou_ln9M7-NWQIY'
API_ID = '23124608'
API_HASH = '0a612aa8f1c8f5eaf60eaadb73ab8e27'

user_data = {}
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)

def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def is_playlist(url):
    return "list=" in url

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_animation(
        animation="https://media.giphy.com/media/3o6Zt481isNVuQI1l6/giphy.gif",
        caption="🎉 Բարի գալուստ մեր մեգա-կрутому боту! 📽️\nՈւղղարկեք Յութուբի լինկը, чтобы начать."
    )

@app.on_message(filters.text & ~filters.command("start"))
async def ask_video_or_audio(client, message):
    url = message.text
    if not re.match(r'(https?://)?(www\.)?(youtube|youtu\.be)(\.com)?/.+', url):
        await message.reply_text('🚫 Տվեք YouTube-ի հղումը:')
        return

    user_data[message.chat.id] = {'url': url}

    try:
        ydl_opts = {'format': 'best', 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnail = info.get('thumbnail', None)
            title = info.get('title', 'Վիդեո')

    except Exception as e:
        await message.reply_text(f'⚠️ Նկարահանման ժամանակ առաջացավ սխալ: {e}')
        return

    await client.send_photo(
        message.chat.id, 
        photo=thumbnail, 
        caption=f"🎬 Ինչ եք ցանկանում  ներբեռնել՝ աուդիո կամ վիդեո: `{title}`",
        reply_markup=video_selection_keyboard()
    )

def video_selection_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎥 Վիդեո", callback_data='video')],
        [InlineKeyboardButton("🎵 Աուդիո", callback_data='audio')]
    ]
    return InlineKeyboardMarkup(keyboard)

def quality_keyboard():
    keyboard = [
        [InlineKeyboardButton("144p", callback_data='144')],
        [InlineKeyboardButton("240p", callback_data='240')],
        [InlineKeyboardButton("360p", callback_data='360')],
        [InlineKeyboardButton("480p", callback_data='480')],
        [InlineKeyboardButton("720p", callback_data='720')],
        [InlineKeyboardButton("1080p", callback_data='1080')],
        [InlineKeyboardButton("🔙 Վերադառնալ", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)

@app.on_callback_query()
async def button_click(client, callback_query):
    await callback_query.answer()
    chat_id = callback_query.message.chat.id
    choice = callback_query.data

    if choice == 'video':
        user_data[chat_id]['choice'] = 'video'
        await callback_query.edit_message_text('📺  Ընտրեք որակը:', reply_markup=quality_keyboard())

    elif choice in ['144', '240', '360', '480', '720', '1080']:
        user_data[chat_id]['quality'] = choice
        await download_video(chat_id, callback_query)  
    elif choice == 'audio':
        user_data[chat_id]['choice'] = 'audio'
        await download_audio(chat_id, callback_query)
    elif choice == 'back':
        await callback_query.edit_message_text('🎬 Ընտրեք ձևաչափ՝ աուդիո կամ վիդեո:', reply_markup=video_selection_keyboard())

async def download_audio(chat_id, callback_query):
    url = user_data[chat_id]['url']
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,  
        }

        os.makedirs('downloads', exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = clean_filename(info.get('title', 'Без названия'))  
            file_name = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

        if os.path.exists(file_name):
            new_file_name = os.path.join('downloads', f"{title}.mp3")
            os.rename(file_name, new_file_name)

            await callback_query.message.reply_audio(
                audio=open(new_file_name, 'rb'),
                title=title,
                performer='@ldftcer',
                caption="📥 @armYouTube_bot | Բոտ от @Ldftcer"
            )

            os.remove(new_file_name) 
        else:
            await callback_query.message.reply_text(f'⚠️ Նկարահանման սխալ: {file_name}')

    except Exception as e:
        await callback_query.message.reply_text(f'⚠️ Սխալ՝ {e}')

async def download_video(chat_id, callback_query):
    url = user_data[chat_id]['url']
    quality = user_data[chat_id]['quality'] 

    try:
        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'noplaylist': True,
        }

        os.makedirs('downloads', exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = clean_filename(info.get('title', 'Без названия'))
            file_name = ydl.prepare_filename(info) 

        mp4_file_name = os.path.join('downloads', f"{title}.mp4")

        command = ['ffmpeg', '-i', file_name, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', mp4_file_name]
        subprocess.run(command, check=True)

        if os.path.exists(mp4_file_name):
            await callback_query.message.reply_video(
                video=open(mp4_file_name, 'rb'),
                caption="📥 @armYouTube_bot | Бот от @Ldftcer"
            )
        else:
            await callback_query.message.reply_text(f'⚠️ Ֆայլը չի գտնվել: {mp4_file_name}')

        if os.path.exists(file_name):
            os.remove(file_name)

    except Exception as e:
        await callback_query.message.reply_text(f'⚠️ Սխալ: {e}')

if __name__ == "__main__":
    app.run()
