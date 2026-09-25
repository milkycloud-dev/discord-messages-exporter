<p align="center"><img src="assets/logo.png" width="128" height="128" alt="Discord Messages Exporter icon"></p>

<h1 align="center">Discord Messages Exporter</h1>

<p align="center">Windows app that saves a Discord channel or direct message history into an offline HTML archive styled like the Discord client, with images, video and audio downloaded next to it.</p>

<p align="center"><a href="https://github.com/milkycloud-dev/discord-messages-exporter/actions/workflows/release.yml"><img src="https://github.com/milkycloud-dev/discord-messages-exporter/actions/workflows/release.yml/badge.svg" alt="Release"></a></p>

<p align="center"><a href="#english">English</a> | <a href="#русский">Русский</a></p>

<a id="english"></a>

## English

### How it works

The app starts a small local server on `127.0.0.1:8089` and gives you a script for the Discord DevTools console. The script scrolls the open chat upwards, collects the rendered messages and sends them to the app. The app sorts them, downloads the attachments and writes one HTML file that opens without internet access.

```
Discord client (console script, auto-scroll) > local server :8089 > sort and merge > attachments > HTML in Exported_Chats/
```

Nothing is sent anywhere except between the Discord window and the app on the same computer.

### Features

- Dark Discord theme, cozy message spacing, Nitro gradient names, avatar decorations placed over the avatar.
- Attachments from `cdn.discordapp.com` and `media.discordapp.net` saved to `attachments/`.
- Full-size images recovered from links when Discord had already unloaded the `<img>` tags.
- Screen-reader duplicates removed from timestamps; short timestamps in the left gutter for grouped messages.
- Emoji and SVG icon paths rewritten so they render offline.
- On-screen counter in Discord with a `Stop & Save` button; the script also stops at the start of the chat.
- One button enables DevTools in Discord Stable, PTB and Canary.
- Interface in English and Russian.

### Requirements

Windows 10 or 11, the Discord desktop client, Python 3.9 or newer when running from source, internet access during the export for the attachments.

### Usage

1. Start the app (`python main.py` or `start.bat`).
2. Click "Unlock DevTools in Discord" and restart Discord.
3. Open the chat you want to save.
4. Press `Ctrl+Shift+I`, open the Console tab, paste the script copied from the app and press Enter.
5. Wait for the start of the chat or click `Stop & Save`. The archive is written to `Exported_Chats/<chat title>/`.

### Discord terms

Scripts in the client console and automated scrolling are outside what Discord allows for user accounts. Use it for your own conversations and at your own risk.

### Releases

A tag `v*` builds `DiscordExporter_Windows.zip` with PyInstaller on GitHub Actions and publishes it with the notes from [CHANGELOG.md](CHANGELOG.md).

### License

Proprietary, all rights reserved. Running the official release builds is allowed; see [LICENSE](LICENSE) for the full terms.

<a id="русский"></a>

## Русский

### Как это работает

Приложение поднимает небольшой локальный сервер на `127.0.0.1:8089` и выдаёт скрипт для консоли DevTools в Discord. Скрипт прокручивает открытый чат вверх, собирает отрисованные сообщения и отправляет их приложению. Приложение сортирует их, скачивает вложения и пишет один HTML-файл, который открывается без интернета.

```
клиент Discord (скрипт в консоли, прокрутка) > локальный сервер :8089 > сортировка и склейка > вложения > HTML в Exported_Chats/
```

Данные ходят только между окном Discord и приложением на том же компьютере.

### Возможности

- Тёмная тема Discord, интервалы Cozy, градиентные ники Nitro, украшения аватаров поверх аватара.
- Вложения с `cdn.discordapp.com` и `media.discordapp.net` сохраняются в `attachments/`.
- Полноразмерные картинки восстанавливаются по ссылкам, даже если Discord уже выгрузил теги `<img>`.
- Из времени убраны дубли для скринридеров; у сгруппированных сообщений короткое время в левой колонке.
- Пути эмодзи и SVG-иконок переписаны, чтобы они отображались офлайн.
- Счётчик на экране Discord с кнопкой `Остановить и сохранить`; в начале чата скрипт останавливается сам.
- Одна кнопка включает DevTools в Discord Stable, PTB и Canary.
- Интерфейс на английском и русском.

### Требования

Windows 10 или 11, клиент Discord для ПК, Python 3.9 или новее при запуске из исходников, интернет во время экспорта для вложений.

### Использование

1. Запустите приложение (`python main.py` или `start.bat`).
2. Нажмите «Разблокировать DevTools в Discord» и перезапустите Discord.
3. Откройте нужный чат.
4. Нажмите `Ctrl+Shift+I`, откройте вкладку Console, вставьте скрипт, скопированный из приложения, и нажмите Enter.
5. Дождитесь начала чата или нажмите `Остановить и сохранить`. Архив появится в `Exported_Chats/<название чата>/`.

### Правила Discord

Скрипты в консоли клиента и автоматическая прокрутка выходят за рамки того, что Discord разрешает для пользовательских аккаунтов. Используйте для своих переписок и на свой риск.

### Релизы

Тег `v*` собирает `DiscordExporter_Windows.zip` через PyInstaller в GitHub Actions и публикует его с описанием из [CHANGELOG.md](CHANGELOG.md).

### Лицензия

Проприетарная, все права защищены. Запуск официальных сборок из релизов разрешён; полные условия в [LICENSE](LICENSE).
