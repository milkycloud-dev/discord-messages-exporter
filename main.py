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
    log_msg(f"Начат экспорт: {chat_title}")
    return jsonify({"status": "ok"})

def download_attachment(url, save_dir):
    try:
        parsed = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"file_{int(time.time())}.dat"
        
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
        log_msg(f"Ошибка скачивания {url}: {e}")
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
    log_msg(f"Получено пакетов сообщений: {len(msgs)} (Всего сохранено: {len(messages_data)})")
    return jsonify({"status": "ok"})

@app.route('/finish', methods=['POST', 'OPTIONS'])
def finish_export():
    if request.method == 'OPTIONS':
        return '', 200
    threading.Thread(target=compile_export).start()
    return jsonify({"status": "ok"})

def compile_export():
    global is_exporting
    log_msg("Начинается обработка HTML и скачивание вложений. Пожалуйста, подождите...")
    
    os.makedirs(export_dir, exist_ok=True)
    base_dir = os.path.join(export_dir, chat_title)
    attachments_dir = os.path.join(base_dir, 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    
    sorted_messages = []
    for k in sorted(messages_data.keys(), key=lambda x: int(x.split('-')[-1]) if '-' in x else 0):
        sorted_messages.append(messages_data[k])
        
    full_body = "".join(sorted_messages)
    soup = BeautifulSoup(full_body, 'html.parser')
    
    targets = []
    for img in soup.find_all('img'):
        if img.get('src') and 'cdn.discordapp.com' in img.get('src'):
            if '/avatars/' in img.get('src') or '/emojis/' in img.get('src') or '/icons/' in img.get('src'):
                continue
            targets.append((img, 'src'))
            
    for source in soup.find_all('source'):
        if source.get('src') and 'cdn.discordapp.com' in source.get('src'):
            targets.append((source, 'src'))
            
    for a in soup.find_all('a'):
        if a.get('href') and 'cdn.discordapp.com/attachments' in a.get('href'):
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
                log_msg(f"Скачивание вложений... {count}/{total}")
            local_filename = download_attachment(url, attachments_dir)
            if local_filename:
                downloaded_urls[url] = local_filename
            time.sleep(0.3 + random.uniform(0, 1.5)) # Рандомизированная задержка (0.3 - 1.8 сек)
                
        if local_filename:
            tag[attr] = f"attachments/{local_filename}"
        count += 1
        
    log_msg("Вложения скачаны. Формирование итогового файла...")
    
    final_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>{chat_title} - Export</title>
    {document_head}
    <style>
        body {{ 
            background-color: #313338 !important; 
            color: #dbdee1; 
            font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif; 
            overflow-y: scroll; 
            margin: 0; 
            padding: 20px 0; 
        }}
        .container-main {{ 
            max-width: 1000px; 
            margin: 0 auto; 
            background: #313338; 
            border-radius: 8px; 
            padding: 20px; 
        }}
        li[class*="messageListItem_"] {{ list-style: none; margin-bottom: 5px; }}
        [class*="scrollerInner_"] {{ min-height: unset !important; }}
        ul, ol {{ padding-left: 0; margin: 0; }}
        img {{ max-width: 100%; height: auto; }}
        a {{ pointer-events: auto !important; }}
        .export-header {{
            max-width: 1000px; margin: 0 auto 20px auto; 
            padding: 20px; border-bottom: 2px solid #2b2d31;
            font-size: 24px; font-weight: bold; color: white;
        }}
    </style>
</head>
<body class="theme-dark">
    <div class="export-header">📁 Экспорт чата: {chat_title}</div>
    <div class="container-main">
        <ul aria-label="Сообщения из чата">
            {soup.decode()}
        </ul>
    </div>
</body>
</html>
"""
    
    out_file = os.path.join(base_dir, f"{chat_title}.html")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    log_msg(f"✅ Готово! Файл сохранен в:\n{out_file}")
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
    log_msg("Сервер запущен. Готов к приему данных из Discord...")
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    try:
        app.run(port=8089, host='0.0.0.0', debug=False, use_reloader=False)
    except Exception as e:
        log_msg(f"ОШИБКА КРИТИЧЕСКАЯ: Ошибка сервера: {e} | Возможно порт 8089 занят.")
def main():
    root = tk.Tk()
    root.title("Discord Chat Exporter")
    root.geometry("650x550")
    root.configure(bg="#2b2d31")
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    def create_btn(parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg="#5865F2", fg="white", 
                         font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=5, cursor="hand2")
                         
    def create_lbl(parent, text, bold=False):
        fnt = ("Helvetica", 11, "bold") if bold else ("Helvetica", 11)
        return tk.Label(parent, text=text, bg="#2b2d31", fg="#dbdee1", 
                        font=fnt, justify="left", wraplength=600)

    create_lbl(root, "Утилита для экспорта переписки Discord с вложениями", bold=True).pack(pady=(15, 10), anchor="center")

    create_lbl(root, "Шаг 1. Разрешите использование консоли в клиенте Discord").pack(pady=(10, 0), anchor="w", padx=20)
    
    def btn_enable_devtools():
        if enable_discord_devtools():
            messagebox.showinfo("Успех", "Режим разработчика активирован! Перезапустите Discord.")
        else:
            messagebox.showwarning("Внимание", "Не удалось найти настройки Discord. Включите Developer Mode вручную.")
            
    create_btn(root, "Разблокировать DevTools в Discord", btn_enable_devtools).pack(pady=5, anchor="w", padx=20)
    
    create_lbl(root, "Шаг 2. Откройте нужный чат. Нажмите Ctrl + Shift + I. Откройте вкладку 'Console'.").pack(pady=(10, 0), anchor="w", padx=20)
    
    def btn_copy_script():
        script = """
(async function() {
    console.log("%c[Discord Exporter] Начинаю работу...", "color: #5865F2; font-size: 20px; font-weight: bold;");
    let SERVER_URL = "http://127.0.0.1:8089";
    try { 
        await fetch(`${SERVER_URL}/ping`); 
    } catch(e) {
        console.warn("127.0.0.1 недоступен, пробуем localhost", e);
        SERVER_URL = "http://localhost:8089";
        try {
            await fetch(`${SERVER_URL}/ping`);
        } catch(e2) {
            alert("ОШИБКА: Доступ к программе блокируется антивирусом или вы закрыли программу на ПК!"); 
            return;
        }
    }
    const titleMatch = document.title.replace(/[^a-zA-Zа-яА-Я0-9_ -]/g, "");
    await fetch(`${SERVER_URL}/init`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ head: document.head.innerHTML, title: titleMatch })
    });
    let msgNode = document.querySelector('li[class*="messageListItem_"]');
    if(!msgNode) { alert("Сообщения не найдены! Вы точно в чате?"); return; }
    let scroller = msgNode.parentElement;
    while(scroller && (!scroller.className || !scroller.className.includes("scroller_"))) {
        scroller = scroller.parentElement;
    }
    let exportedIds = new Set();
    let keepScrolling = true;
    let uiLayer = document.createElement("div");
    uiLayer.style = "position:fixed;top:20px;right:20px;z-index:999999;background:#1e1f22;padding:25px;border-radius:10px;box-shadow:0 0 15px rgba(0,0,0,0.8);color:white;text-align:center;font-family:sans-serif;";
    let stopBtn = document.createElement("button");
    stopBtn.innerText = "🛑 Остановить и Сохранить";
    stopBtn.style = "background:#5865F2;color:white;border:none;padding:12px 24px;font-size:16px;font-weight:bold;border-radius:6px;cursor:pointer;margin-top:10px;";
    let statusTxt = document.createElement("div");
    statusTxt.innerText = "Собрано: 0 сообщений";
    statusTxt.style = "font-weight:bold;font-size:20px;margin-bottom:10px;color:#5865f2;";
    uiLayer.appendChild(statusTxt); uiLayer.appendChild(stopBtn); document.body.appendChild(uiLayer);
    
    stopBtn.onclick = async () => {
        if(!keepScrolling) return; keepScrolling = false;
        stopBtn.innerText = "⏳ Сохраняем..."; stopBtn.style.background = "#ED4245";
        await fetch(`${SERVER_URL}/finish`, {method: "POST"});
        uiLayer.remove();
        alert("Остановлено! Смотрите окно программы.");
    };
    while (keepScrolling) {
        let messages = Array.from(document.querySelectorAll('li[class*="messageListItem_"]'));
        let newMessagesData = [];
        for (let msg of messages) {
            let id = msg.id;
            if (!id || exportedIds.has(id)) continue;
            exportedIds.add(id);
            newMessagesData.push({ id: id, html: msg.outerHTML });
        }
        if (newMessagesData.length > 0) {
            statusTxt.innerText = `Собрано: ${exportedIds.size} сообщений`;
            await fetch(`${SERVER_URL}/chunk`, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ messages: newMessagesData })
            });
        }
        let oldScrollPos = scroller.scrollTop;
        scroller.scrollTop -= 700; 
        let scrollDelay = 1800 + Math.floor(Math.random() * 1500);
        await new Promise(r => setTimeout(r, scrollDelay)); // Увеличенная рандомизированная задержка (1.8 - 3.3 сек)
        if (scroller.scrollTop === oldScrollPos && scroller.scrollTop === 0) {
            let topDelay = 3500 + Math.floor(Math.random() * 1500);
            await new Promise(r => setTimeout(r, topDelay)); // Ждем подгрузку (3.5 - 5.0 сек)
            if (document.querySelectorAll('li[class*="messageListItem_"]').length === messages.length) {
                if(!keepScrolling) break; keepScrolling = false;
                await fetch(`${SERVER_URL}/finish`, {method: "POST"});
                uiLayer.remove();
                alert("Достигнуто начало чата! Открывайте программу.");
            }
        }
    }
})();
        """
        root.clipboard_clear()
        root.clipboard_append(script.strip())
        messagebox.showinfo("Скопировано", "Скрипт скопирован! Вставьте в Console Discord, нажмите Enter.")
        
    create_lbl(root, "Шаг 3. Скопируйте магический скрипт и вставьте его в Консоль (Console).").pack(pady=(10, 0), anchor="w", padx=20)
    create_btn(root, "📋 Скопировать скрипт", btn_copy_script).pack(pady=5, anchor="w", padx=20)

    log_area = scrolledtext.ScrolledText(root, height=10, bg="#1e1f22", fg="#dbdee1", font=("Consolas", 10), state="normal", borderwidth=0)
    log_area.pack(padx=20, pady=(15, 20), fill=tk.BOTH, expand=True)
    
    root.after(100, gui_loop, root, log_area)
    root.mainloop()

if __name__ == "__main__":
    main()
