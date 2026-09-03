import os
import re
import json
import time
import random
import threading
import queue
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import tkinter as tk
from tkinter import messagebox, scrolledtext

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

messages_data = {} 
document_head = ""
chat_title = "Discord_Export"
logs_queue = queue.Queue()
is_exporting = False
export_dir = os.path.join(os.getcwd(), 'Exported_Chats')

current_lang = 'en'

TRANSLATIONS = {
    'en': {
        'win_title': 'Discord Messages Exporter',
        'subtitle': 'Utility to export Discord chat history with attachments',
        'step1': 'Step 1. Enable Developer Mode / Console in your Discord client:',
        'btn_devtools': 'Unlock DevTools in Discord',
        'step2': 'Step 2. Open the desired chat in Discord, press Ctrl + Shift + I, and open the "Console" tab.',
        'step3': 'Step 3. Copy the script below, paste it into the Discord Console, and press Enter:',
        'btn_copy': '📋 Copy Exporter Script',
        'copied_title': 'Copied',
        'copied_msg': 'Script copied to clipboard! Paste it into Discord Console and press Enter.',
        'success_title': 'Success',
        'devtools_success': 'Developer Mode enabled! Please restart your Discord client.',
        'warn_title': 'Notice',
        'devtools_fail': 'Could not locate Discord settings automatically. Please enable Developer Mode manually.',
        'server_ready': 'Server started on port 8089. Ready to receive data from Discord...',
        'server_error': 'CRITICAL ERROR: Server error: {e} | Port 8089 might be in use.',
        'export_start': 'Export started: {title}',
        'batch_recv': 'Received message batch: {count} (Total collected: {total})',
        'compile_start': 'Processing HTML and downloading attachments. Please wait...',
        'downloading': 'Downloading attachments... {count}/{total}',
        'post_process': 'Attachments downloaded. Post-processing message structure...',
        'done': '✅ Done! File saved to:\n{out_file}',
        'download_error': 'Error downloading {url}: {e}',
        'html_title_suffix': 'Chat Export',
        'html_header_stats': 'Messages: {total}',
        'lang_label': 'Language:',
        'js_start': '[Discord Exporter] Starting...',
        'js_err_connect': 'ERROR: Access to the exporter app is blocked by firewall/antivirus or the app was closed!',
        'js_err_not_chat': 'Messages not found! Are you sure you are in a chat?',
        'js_btn_stop': '🛑 Stop & Save',
        'js_btn_saving': '⏳ Saving...',
        'js_status_init': 'Collected: 0 messages',
        'js_status_prefix': 'Collected:',
        'js_status_suffix': 'messages',
        'js_alert_stopped': 'Export stopped! Check the exporter app window.',
        'js_alert_reached_top': 'Reached the beginning of chat! Check the exporter app window.'
    },
    'ru': {
        'win_title': 'Discord Messages Exporter',
        'subtitle': 'Утилита для экспорта переписки Discord с вложениями',
        'step1': 'Шаг 1. Разрешите использование консоли (DevTools) в клиенте Discord:',
        'btn_devtools': 'Разблокировать DevTools в Discord',
        'step2': 'Шаг 2. Откройте нужный чат в Discord, нажмите Ctrl + Shift + I и откройте вкладку «Console».',
        'step3': 'Шаг 3. Скопируйте скрипт ниже, вставьте его в Консоль (Console) и нажмите Enter:',
        'btn_copy': '📋 Скопировать скрипт',
        'copied_title': 'Скопировано',
        'copied_msg': 'Скрипт скопирован! Вставьте в Console Discord и нажмите Enter.',
        'success_title': 'Успех',
        'devtools_success': 'Режим разработчика активирован! Перезапустите Discord.',
        'warn_title': 'Внимание',
        'devtools_fail': 'Не удалось найти настройки Discord. Включите Developer Mode вручную.',
        'server_ready': 'Сервер запущен. Готов к приему данных из Discord...',
        'server_error': 'ОШИБКА КРИТИЧЕСКАЯ: Ошибка сервера: {e} | Возможно порт 8089 занят.',
        'export_start': 'Начат экспорт: {title}',
        'batch_recv': 'Получено пакетов сообщений: {count} (Всего сохранено: {total})',
        'compile_start': 'Начинается обработка HTML и скачивание вложений. Пожалуйста, подождите...',
        'downloading': 'Скачивание вложений... {count}/{total}',
        'post_process': 'Вложения скачаны. Пост-обработка структуры сообщений...',
        'done': '✅ Готово! Файл сохранен в:\n{out_file}',
        'download_error': 'Ошибка скачивания {url}: {e}',
        'html_title_suffix': 'Экспорт сообщений',
        'html_header_stats': 'Сообщений: {total}',
        'lang_label': 'Язык:',
        'js_start': '[Discord Exporter] Начинаю работу...',
        'js_err_connect': 'ОШИБКА: Доступ к программе блокируется антивирусом или вы закрыли программу на ПК!',
        'js_err_not_chat': 'Сообщения не найдены! Вы точно в чате?',
        'js_btn_stop': '🛑 Остановить и сохранить',
        'js_btn_saving': '⏳ Сохраняем...',
        'js_status_init': 'Собрано: 0 сообщений',
        'js_status_prefix': 'Собрано:',
        'js_status_suffix': 'сообщений',
        'js_alert_stopped': 'Остановлено! Смотрите окно программы.',
        'js_alert_reached_top': 'Достигнуто начало чата! Открывайте программу.'
    }
}

def t(key, **kwargs):
    text = TRANSLATIONS.get(current_lang, TRANSLATIONS['en']).get(key, '')
    if kwargs:
        return text.format(**kwargs)
    return text

def log_msg(msg):
    print(msg)
    logs_queue.put(msg)

@app.route('/ping', methods=['GET'])
def ping():
    return 'PONG'

@app.route('/init', methods=['POST', 'OPTIONS'])
def init_export():
    if request.method == 'OPTIONS':
        return '', 200
    global document_head, chat_title, messages_data, is_exporting
    data = request.json
    document_head = data.get('head', '')
    title_raw = data.get('title', 'Discord_Export')
    chat_title = "".join(x for x in title_raw if x.isalnum() or x in " -_А-Яа-я")
    if not chat_title: chat_title = f"Chat_{int(time.time())}"
    
    messages_data = {}
    is_exporting = True
    log_msg(t("export_start", title=chat_title))
    return jsonify({"status": "ok"})

DISCORD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-primary: #313338;
    --bg-secondary: #2b2d31;
    --bg-tertiary: #1e1f22;
    --text-normal: #dbdee1;
    --text-muted: #949ba4;
    --header-primary: #f2f3f5;
    --interactive-normal: #b5bac1;
    --interactive-hover: #dcdee1;
    --interactive-active: #ffffff;
    --brand-500: #5865f2;
}

* {
    box-sizing: border-box;
}

body {
    background-color: var(--bg-primary) !important;
    color: var(--text-normal);
    font-family: 'gg sans', 'Inter', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 0;
    line-height: 1.375rem;
    overflow-y: scroll;
    -webkit-font-smoothing: antialiased;
}

/* Chat Header Banner */
.discord-header-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    height: 52px;
    background-color: rgba(43, 45, 49, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(0, 0, 0, 0.28);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.discord-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
}

.discord-channel-icon {
    font-size: 22px;
    color: var(--text-muted);
    font-weight: 400;
    line-height: 1;
}

.discord-channel-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--header-primary);
    letter-spacing: -0.2px;
}

.discord-header-stats {
    font-size: 12px;
    color: var(--text-muted);
    background: rgba(0, 0, 0, 0.25);
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 500;
}

/* Chat Area Container */
.chat-container {
    max-width: 1060px;
    margin: 0 auto;
    padding: 20px 16px 80px 16px;
}

ul[aria-label="Сообщения из чата"], ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

/* Message List Item */
li[class*="messageListItem_"] {
    list-style: none;
    margin: 0;
    padding: 0;
    position: relative;
}

/* Base Message Box */
[class*="message_"] {
    position: relative;
    padding: 2px 16px 2px 72px;
    min-height: 1.375rem;
    font-size: 1rem;
    line-height: 1.375rem;
    box-sizing: border-box;
    user-select: text;
    border-radius: 4px;
    margin: 0;
}

[class*="message_"]:hover {
    background-color: rgba(2, 2, 2, 0.07);
}

/* Group Start */
[class*="groupStart_"] {
    margin-top: 17px;
    min-height: 2.75rem;
}

[class*="hasReply_"] {
    margin-top: 20px !important;
}

/* Contents wrapper */
[class*="contents_"] {
    position: relative;
    width: 100%;
}

/* Avatar Styling */
[class*="avatar_"] {
    position: absolute;
    left: -56px;
    top: 2px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    overflow: hidden;
    cursor: pointer;
    user-select: none;
    flex-shrink: 0;
    z-index: 2;
    object-fit: cover;
    transition: transform 0.1s ease;
}

[class*="avatar_"]:hover {
    transform: scale(1.05);
}

/* Avatar Decoration - centered directly over the 40px avatar */
[class*="avatarDecoration_"] {
    position: absolute;
    left: -62px;
    top: -4px;
    width: 52px;
    height: 52px;
    pointer-events: none;
    z-index: 3;
    object-fit: contain;
}

/* Compact Timestamps in Left Gutter */
[class*="timestampVisibleOnHover_"], [class*="latin12CompactTimeStamp_"] {
    position: absolute;
    left: -72px;
    top: 2px;
    width: 56px;
    text-align: right;
    font-size: 0.6875rem;
    line-height: 1.375rem;
    color: var(--text-muted);
    user-select: none;
    cursor: default;
    opacity: 0;
    transition: opacity 0.1s ease;
    white-space: nowrap;
}

[class*="message_"]:hover [class*="timestampVisibleOnHover_"],
[class*="message_"]:hover [class*="latin12CompactTimeStamp_"] {
    opacity: 0.8;
}

[class*="timestampVisibleOnHover_"] [class*="separator_"],
[class*="latin12CompactTimeStamp_"] [class*="separator_"] {
    display: none !important;
}

/* Screen reader text MUST be hidden */
[class*="hiddenVisually_"] {
    display: none !important;
}

/* Header (Author + Timestamp) */
[class*="header_"] {
    display: flex;
    align-items: baseline;
    line-height: 1.375rem;
    min-height: 1.375rem;
    color: var(--text-muted);
    margin: 0 0 2px 0;
    white-space: normal;
}

[class*="headerText_"] {
    display: inline-flex;
    align-items: baseline;
    margin-right: 0.25rem;
    white-space: normal;
}

[class*="username_"] {
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.375rem;
    color: var(--header-primary);
    display: inline;
    vertical-align: baseline;
    cursor: pointer;
    white-space: nowrap;
}

[class*="username_"]:hover {
    text-decoration: underline;
}

/* Custom Display Name (Nitro gradient prism text) */
[class*="prism_"] {
    background: linear-gradient(90deg, var(--custom-display-name-styles-prism-stops, #f2f3f5, #f2f3f5)) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    color: transparent !important;
    display: inline-block;
    font-weight: 600;
}

/* Inline Timestamp next to username */
[class*="timestampInline_"], [class*="timestamp_"]:not([class*="timestampVisibleOnHover_"]):not([class*="latin12CompactTimeStamp_"]) {
    display: inline-flex;
    align-items: baseline;
    font-size: 0.75rem;
    line-height: 1.375rem;
    color: var(--text-muted);
    vertical-align: baseline;
    margin-left: 0.25rem;
    font-weight: 400;
    cursor: default;
    white-space: nowrap;
}

[class*="separator_"] {
    display: inline-block;
    margin: 0 4px;
    color: var(--text-muted);
    opacity: 0.5;
    font-style: normal;
    font-size: 0.75rem;
}

/* Message Content Text */
[class*="messageContent_"] {
    user-select: text;
    margin: 0;
    padding: 0;
    color: var(--text-normal);
    font-weight: 400;
    font-size: 1rem;
    line-height: 1.375rem;
    white-space: pre-wrap;
    word-break: break-word;
}

/* Links */
a, [class*="anchor_"] {
    color: #00a8fc !important;
    text-decoration: none;
    cursor: pointer;
}

a:hover, [class*="anchor_"]:hover {
    text-decoration: underline;
}

/* Replied Message Preview */
[class*="repliedMessage_"] {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.875rem;
    line-height: 1.125rem;
    color: var(--interactive-normal);
    margin-bottom: 4px;
    position: relative;
    user-select: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    height: 18px;
}

[class*="repliedMessage_"] [class*="repliedMessageClickableSpine_"] {
    position: absolute;
    left: -36px;
    top: 10px;
    width: 28px;
    height: calc(100% + 4px);
    border-left: 2px solid #4e5058;
    border-top: 2px solid #4e5058;
    border-top-left-radius: 6px;
    box-sizing: border-box;
    pointer-events: none;
}

[class*="replyAvatar_"] {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    margin-right: 2px;
    user-select: none;
    flex-shrink: 0;
    object-fit: cover;
}

[class*="repliedMessage_"] [class*="username_"] {
    font-size: 0.875rem;
    line-height: 1.125rem;
    font-weight: 500;
    color: var(--interactive-normal);
    opacity: 0.9;
}

[class*="repliedTextPreview_"] {
    display: inline-flex;
    align-items: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
}

[class*="repliedTextContent_"] {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
    font-size: 0.875rem;
}

/* Emojis */
.emoji, [class*="emoji_"] {
    width: 1.375em;
    height: 1.375em;
    vertical-align: -0.25em;
    object-fit: contain;
    display: inline-block;
}

.emoji.jumboable {
    width: 3rem;
    height: 3rem;
    min-height: 3rem;
}

/* Code & Pre Blocks */
code {
    background: #2b2d31;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Consolas', 'Courier New', Courier, monospace;
    font-size: 85%;
    color: #dbdee1;
}

pre {
    background: #2b2d31;
    border: 1px solid #1e1f22;
    border-radius: 4px;
    padding: 0;
    margin: 6px 0;
    font-family: 'Consolas', 'Courier New', Courier, monospace;
    font-size: 0.875rem;
    line-height: 1.125rem;
    max-width: 90%;
    overflow: hidden;
}

pre code {
    display: block;
    padding: 10px;
    overflow-x: auto;
    color: #dbdee1;
    background: transparent;
    border: none;
    font-size: 0.875rem;
    line-height: 1.125rem;
}

.hljs-keyword, .hljs-built_in { color: #f47067; }
.hljs-string { color: #96d0ff; }
.hljs-number { color: #6bc46d; }
.hljs-comment { color: #8b949e; font-style: italic; }
.hljs-title, .hljs-function { color: #d2a8ff; }

/* Blockquotes */
[class*="blockquoteContainer_"] {
    display: flex;
    margin: 4px 0;
}

[class*="blockquoteDivider_"] {
    width: 4px;
    border-radius: 4px;
    background-color: #4e5058;
    margin-right: 12px;
    flex-shrink: 0;
}

/* Embeds */
[class*="embed_"], [class*="embedFull_"] {
    display: inline-grid;
    grid-template-columns: auto;
    grid-template-rows: auto;
    box-sizing: border-box;
    position: relative;
    max-width: 520px;
    background-color: #2b2d31;
    border-left: 4px solid #1e1f22;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-top: 6px;
    color: var(--text-normal);
}

[class*="embedTitle_"] {
    font-size: 1rem;
    font-weight: 600;
    margin: 4px 0;
}

[class*="embedProvider_"] {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--text-muted);
}

[class*="embedDescription_"] {
    font-size: 0.875rem;
    line-height: 1.125rem;
    font-weight: 400;
    color: var(--text-normal);
    margin-top: 4px;
}

[class*="hasThumbnail_"] {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
}

[class*="embedThumbnail_"] {
    grid-column: 2;
    justify-self: end;
    border-radius: 4px;
    overflow: hidden;
    max-width: 80px;
    max-height: 80px;
}

/* Media, Attachments, Images */
[class*="container_b7e1cb"], [id*="message-accessories-"] {
    display: grid;
    grid-auto-flow: row;
    grid-row-gap: 0.25rem;
    text-indent: 0;
    min-height: 0;
    min-width: 0;
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
}

[class*="imageWrapper_"], [class*="imageContainer_"] {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    max-width: 550px;
    max-height: 400px;
    display: inline-block;
    background-color: transparent !important;
}

[class*="loadingOverlay_"] {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    max-width: 550px;
    max-height: 400px;
    display: inline-block;
    background-color: transparent !important;
}

[class*="loadingOverlay_"]:empty {
    display: none !important;
}

[class*="lazyImg_"] {
    max-width: 100%;
    max-height: 400px;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 8px;
    display: block;
}

/* Reactions */
[class*="reactions_"] {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
    user-select: none;
}

[class*="reaction_"], [class*="reactionInner_"] {
    display: inline-flex;
    align-items: center;
    background-color: #2b2d31;
    border: 1px solid #383a40;
    border-radius: 8px;
    padding: 2px 6px;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--interactive-normal);
    font-weight: 500;
}

[class*="reactionCount_"] {
    margin-left: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

[class*="reactionBtn_"] {
    display: none !important;
}

/* Mentions */
[class*="mention"], span[class*="wrapper_"][role="button"] {
    color: #c9cdfb !important;
    background: hsla(235, 85.6%, 64.7%, 0.15) !important;
    padding: 0 4px;
    border-radius: 3px;
    font-weight: 500;
}

span[class*="wrapper_"][role="button"]:hover {
    background: hsla(235, 85.6%, 64.7%, 0.3) !important;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #2b2d31;
}
::-webkit-scrollbar-thumb {
    background: #1a1b1e;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #111214;
}
"""

def download_attachment(url, save_dir):
    try:
        parsed = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename or '.' not in filename:
            if 'avatar-decoration' in url or 'static' in filename:
                filename = f"{filename or 'decoration'}.png"
            else:
                filename = f"{filename or 'file'}.dat"
        
        unique_filename = f"{int(time.time()*1000)}_{filename}"
        filepath = os.path.join(save_dir, unique_filename)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, stream=True, timeout=15, headers=headers)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return unique_filename
    except Exception as e:
        log_msg(t("download_error", url=url, e=e))
    return None

@app.route('/chunk', methods=['POST', 'OPTIONS'])
def receive_chunk():
    if request.method == 'OPTIONS':
        return '', 200
    global messages_data
    data = request.json
    msgs = data.get('messages', [])
    for m in msgs:
        mid = m.get('id')
        html = m.get('html')
        messages_data[mid] = html
    log_msg(t("batch_recv", count=len(msgs), total=len(messages_data)))
    return jsonify({"status": "ok"})

@app.route('/finish', methods=['POST', 'OPTIONS'])
def finish_export():
    if request.method == 'OPTIONS':
        return '', 200
    threading.Thread(target=compile_export).start()
    return jsonify({"status": "ok"})

def compile_export():
    global is_exporting
    log_msg(t("compile_start"))
    
    os.makedirs(export_dir, exist_ok=True)
    base_dir = os.path.join(export_dir, chat_title)
    attachments_dir = os.path.join(base_dir, 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    
    def get_sort_key(k):
        try:
            parts = k.split('-')
            for p in reversed(parts):
                if p.isdigit():
                    return int(p)
            return 0
        except Exception:
            return 0

    sorted_messages = []
    for k in sorted(messages_data.keys(), key=get_sort_key):
        sorted_messages.append(messages_data[k])
        
    full_body = "".join(sorted_messages)
    soup = BeautifulSoup(full_body, 'html.parser')
    
    discord_media_domains = [
        'cdn.discordapp.com',
        'media.discordapp.net',
        'images-ext-1.discordapp.net',
        'images-ext-2.discordapp.net'
    ]

    targets = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and any(d in src for d in discord_media_domains):
            if '/avatars/' in src or '/emojis/' in src or '/icons/' in src:
                continue
            targets.append((img, 'src'))
            
    for source in soup.find_all('source'):
        src = source.get('src')
        if src and any(d in src for d in discord_media_domains):
            targets.append((source, 'src'))
            
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and ('/attachments/' in href or any(d in href for d in discord_media_domains)):
            targets.append((a, 'href'))
            
    count = 0
    total = len(targets)
    downloaded_urls = {}
    for tag, attr in targets:
        url = tag.get(attr)
        if not url:
            continue
            
        if url in downloaded_urls:
            local_filename = downloaded_urls[url]
        else:
            if total > 0 and count % 5 == 0:
                log_msg(t("downloading", count=count, total=total))
            local_filename = download_attachment(url, attachments_dir)
            if local_filename:
                downloaded_urls[url] = local_filename
            time.sleep(0.3 + random.uniform(0, 1.5))
                
        if local_filename:
            tag[attr] = f"attachments/{local_filename}"
        count += 1
        
    log_msg(t("post_process"))

    # 1. Fix relative /assets/ emoji urls
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src.startswith('/assets/'):
            img['src'] = f"https://discord.com{src}"

    # 2. Remove low-res placeholder blur overlays
    for p in soup.find_all(lambda t: t.get('class') and any('imagePlaceholder' in c for c in t.get('class'))):
        p.decompose()

    # 3. Restore missing <img> elements inside empty imageWrapper/loadingOverlay containers
    for a in soup.find_all(lambda t: t.name == 'a' and any('originalLink' in c for c in t.get('class', []))):
        href = a.get('href') or a.get('data-safe-src')
        if href and (any(href.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']) or 'attachments/' in href):
            wrapper = a.find_parent(lambda t: t.get('class') and any('imageWrapper' in c for c in t.get('class')))
            if wrapper and not wrapper.find('img'):
                overlay = wrapper.find(lambda t: t.get('class') and any('loadingOverlay' in c for c in t.get('class')))
                if overlay:
                    new_img = soup.new_tag('img', **{
                        'class': 'lazyImg_f4758a',
                        'src': href,
                        'alt': 'Attachment',
                        'style': 'display: block; object-fit: contain; max-width: 100%; max-height: 400px; border-radius: 8px;'
                    })
                    overlay.append(new_img)

    # 4. Clean up head tags from scripts and dead preloads
    clean_head = BeautifulSoup(document_head, 'html.parser')
    for bad_tag in clean_head.find_all(['script', 'link']):
        if bad_tag.name == 'script' or (bad_tag.name == 'link' and bad_tag.get('as') == 'script'):
            bad_tag.decompose()
        elif bad_tag.name == 'link' and bad_tag.get('href', '').startswith('/assets/'):
            bad_tag.decompose()

    total_msgs = len(messages_data)

    final_html = f"""<!DOCTYPE html>
<html lang="{current_lang}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chat_title} - {t('html_title_suffix')}</title>
    {clean_head.decode() if clean_head else ""}
    <style>
{DISCORD_CSS}
    </style>
</head>
<body class="theme-dark">
    <header class="discord-header-bar">
        <div class="discord-header-left">
            <span class="discord-channel-icon">@</span>
            <span class="discord-channel-title">{chat_title}</span>
        </div>
        <div class="discord-header-stats">
            {t('html_header_stats', total=total_msgs)}
        </div>
    </header>
    <main class="chat-container">
        <ul aria-label="Messages">
            {soup.decode()}
        </ul>
    </main>
</body>
</html>
"""
    
    final_html = re.sub(r'url\(([\'"]?)/assets/', r'url(\1https://discord.com/assets/', final_html)
    final_html = re.sub(r'src=([\'"])/assets/', r'src=\1https://discord.com/assets/', final_html)
    final_html = re.sub(r'href=([\'"])/assets/', r'href=\1https://discord.com/assets/', final_html)
    
    out_file = os.path.join(base_dir, f"{chat_title}.html")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    log_msg(t("done", out_file=out_file))
    is_exporting = False


def enable_discord_devtools():
    appdata = os.environ.get('APPDATA')
    if not appdata: return False
    paths = [
        os.path.join(appdata, 'discord', 'settings.json'),
        os.path.join(appdata, 'discordptb', 'settings.json'),
        os.path.join(appdata, 'discordcanary', 'settings.json')
    ]
    success = False
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data['DANGEROUS_ENABLE_DEVTOOLS_ONLY_ENABLE_IF_YOU_KNOW_WHAT_YOURE_DOING'] = True
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                success = True
            except Exception as e:
                pass
    return success


def gui_loop(root, text_widget):
    try:
        while True:
            msg = logs_queue.get_nowait()
            text_widget.insert(tk.END, f"> {msg}\n")
            text_widget.see(tk.END)
    except queue.Empty:
        pass
    root.after(100, gui_loop, root, text_widget)

def run_flask():
    log_msg(t("server_ready"))
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    try:
        app.run(port=8089, host='0.0.0.0', debug=False, use_reloader=False)
    except Exception as e:
        log_msg(t("server_error", e=e))

def main():
    root = tk.Tk()
    root.title(t("win_title"))
    root.geometry("680x580")
    root.configure(bg="#2b2d31")
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    def create_btn(parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg="#5865F2", fg="white", 
                         font=("Helvetica", 11, "bold"), relief="flat", padx=12, pady=6, cursor="hand2")
                         
    def create_lbl(parent, text, bold=False):
        fnt = ("Helvetica", 11, "bold") if bold else ("Helvetica", 11)
        return tk.Label(parent, text=text, bg="#2b2d31", fg="#dbdee1", 
                        font=fnt, justify="left", wraplength=640)

    # Top Bar: Subtitle on left, Language switcher on right
    top_bar = tk.Frame(root, bg="#2b2d31")
    top_bar.pack(fill=tk.X, padx=20, pady=(15, 10))

    lbl_subtitle = tk.Label(top_bar, text=t("subtitle"), bg="#2b2d31", fg="#f2f3f5",
                            font=("Helvetica", 11, "bold"), justify="left", wraplength=460)
    lbl_subtitle.pack(side=tk.LEFT, anchor="w")

    lang_frame = tk.Frame(top_bar, bg="#2b2d31")
    lang_frame.pack(side=tk.RIGHT, anchor="e")

    lbl_lang = tk.Label(lang_frame, text=t("lang_label"), bg="#2b2d31", fg="#949ba4", font=("Helvetica", 10))
    lbl_lang.pack(side=tk.LEFT, padx=(0, 6))

    btn_lang_en = tk.Button(lang_frame, text="EN", command=lambda: set_language("en"),
                            bg="#5865F2", fg="white", font=("Helvetica", 10, "bold"),
                            relief="flat", padx=8, pady=3, cursor="hand2")
    btn_lang_en.pack(side=tk.LEFT, padx=2)

    btn_lang_ru = tk.Button(lang_frame, text="RU", command=lambda: set_language("ru"),
                            bg="#383a40", fg="#949ba4", font=("Helvetica", 10, "bold"),
                            relief="flat", padx=8, pady=3, cursor="hand2")
    btn_lang_ru.pack(side=tk.LEFT, padx=2)

    # Step 1
    lbl_step1 = create_lbl(root, t("step1"))
    lbl_step1.pack(pady=(10, 0), anchor="w", padx=20)
    
    def btn_enable_devtools():
        if enable_discord_devtools():
            messagebox.showinfo(t("success_title"), t("devtools_success"))
        else:
            messagebox.showwarning(t("warn_title"), t("devtools_fail"))
            
    btn_devtools = create_btn(root, t("btn_devtools"), btn_enable_devtools)
    btn_devtools.pack(pady=5, anchor="w", padx=20)
    
    # Step 2
    lbl_step2 = create_lbl(root, t("step2"))
    lbl_step2.pack(pady=(10, 0), anchor="w", padx=20)
    
    # Step 3
    def get_injected_script():
        return f"""
(async function() {{
    console.log("%c{t('js_start')}", "color: #5865F2; font-size: 20px; font-weight: bold;");
    let SERVER_URL = "http://127.0.0.1:8089";
    try {{ 
        await fetch(`${{SERVER_URL}}/ping`); 
    }} catch(e) {{
        console.warn("127.0.0.1 unreachable, trying localhost...", e);
        SERVER_URL = "http://localhost:8089";
        try {{ 
            await fetch(`${{SERVER_URL}}/ping`); 
        }} catch(e2) {{
            alert("{t('js_err_connect')}"); 
            return;
        }}
    }}
    const titleMatch = document.title.replace(/[^a-zA-Zа-яА-Я0-9_ -]/g, "");
    await fetch(`${{SERVER_URL}}/init`, {{
        method: "POST", headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{ head: document.head.innerHTML, title: titleMatch }})
    }});
    let msgNode = document.querySelector('li[class*="messageListItem_"]');
    if(!msgNode) {{ alert("{t('js_err_not_chat')}"); return; }}
    let scroller = msgNode.parentElement;
    while(scroller && (!scroller.className || !scroller.className.includes("scroller_"))) {{
        scroller = scroller.parentElement;
    }}
    let exportedIds = new Set();
    let keepScrolling = true;
    let uiLayer = document.createElement("div");
    uiLayer.style = "position:fixed;top:20px;right:20px;z-index:999999;background:#1e1f22;padding:25px;border-radius:10px;box-shadow:0 0 15px rgba(0,0,0,0.8);color:white;text-align:center;font-family:sans-serif;";
    let stopBtn = document.createElement("button");
    stopBtn.innerText = "{t('js_btn_stop')}";
    stopBtn.style = "background:#5865F2;color:white;border:none;padding:12px 24px;font-size:16px;font-weight:bold;border-radius:6px;cursor:pointer;margin-top:10px;";
    let statusTxt = document.createElement("div");
    statusTxt.innerText = "{t('js_status_init')}";
    statusTxt.style = "font-weight:bold;font-size:20px;margin-bottom:10px;color:#5865f2;";
    uiLayer.appendChild(statusTxt); uiLayer.appendChild(stopBtn); document.body.appendChild(uiLayer);
    
    stopBtn.onclick = async () => {{
        if(!keepScrolling) return; keepScrolling = false;
        stopBtn.innerText = "{t('js_btn_saving')}"; stopBtn.style.background = "#ED4245";
        await fetch(`${{SERVER_URL}}/finish`, {{method: "POST"}});
        uiLayer.remove();
        alert("{t('js_alert_stopped')}");
    }};
    while (keepScrolling) {{
        let messages = Array.from(document.querySelectorAll('li[class*="messageListItem_"]'));
        let newMessagesData = [];
        for (let msg of messages) {{
            let id = msg.id;
            if (!id || exportedIds.has(id)) continue;
            exportedIds.add(id);
            newMessagesData.push({{ id: id, html: msg.outerHTML }});
        }}
        if (newMessagesData.length > 0) {{
            statusTxt.innerText = "{t('js_status_prefix')} " + exportedIds.size + " {t('js_status_suffix')}";
            await fetch(`${{SERVER_URL}}/chunk`, {{
                method: "POST", headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{ messages: newMessagesData }})
            }});
        }}
        let oldScrollPos = scroller.scrollTop;
        scroller.scrollTop -= 700; 
        let scrollDelay = 1800 + Math.floor(Math.random() * 1500);
        await new Promise(r => setTimeout(r, scrollDelay));
        if (scroller.scrollTop === oldScrollPos && scroller.scrollTop === 0) {{
            let topDelay = 3500 + Math.floor(Math.random() * 1500);
            await new Promise(r => setTimeout(r, topDelay));
            if (document.querySelectorAll('li[class*="messageListItem_"]').length === messages.length) {{
                if(!keepScrolling) break; keepScrolling = false;
                await fetch(`${{SERVER_URL}}/finish`, {{method: "POST"}});
                uiLayer.remove();
                alert("{t('js_alert_reached_top')}");
            }}
        }}
    }}
}})();
"""

    def btn_copy_script():
        script = get_injected_script().strip()
        root.clipboard_clear()
        root.clipboard_append(script)
        messagebox.showinfo(t("copied_title"), t("copied_msg"))
        
    lbl_step3 = create_lbl(root, t("step3"))
    lbl_step3.pack(pady=(10, 0), anchor="w", padx=20)
    btn_copy = create_btn(root, t("btn_copy"), btn_copy_script)
    btn_copy.pack(pady=5, anchor="w", padx=20)

    def set_language(lang):
        global current_lang
        current_lang = lang
        root.title(t("win_title"))
        lbl_subtitle.config(text=t("subtitle"))
        lbl_lang.config(text=t("lang_label"))
        lbl_step1.config(text=t("step1"))
        btn_devtools.config(text=t("btn_devtools"))
        lbl_step2.config(text=t("step2"))
        lbl_step3.config(text=t("step3"))
        btn_copy.config(text=t("btn_copy"))

        if lang == 'en':
            btn_lang_en.config(bg="#5865F2", fg="white")
            btn_lang_ru.config(bg="#383a40", fg="#949ba4")
        else:
            btn_lang_ru.config(bg="#5865F2", fg="white")
            btn_lang_en.config(bg="#383a40", fg="#949ba4")

    log_area = scrolledtext.ScrolledText(root, height=10, bg="#1e1f22", fg="#dbdee1", font=("Consolas", 10), state="normal", borderwidth=0)
    log_area.pack(padx=20, pady=(15, 20), fill=tk.BOTH, expand=True)
    
    root.after(100, gui_loop, root, log_area)
    root.mainloop()

if __name__ == "__main__":
    main()
