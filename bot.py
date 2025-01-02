from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from notion_client import Client
import speech_recognition as sr
from gtts import gTTS
import os
import tempfile

# Notion API token và database ID
NOTION_TOKEN = "ntn_s49768200397wZNCawC9OpXBmPfzUQEIEMejFTts7Dd2mx"
DATABASE_ID = "140128a43f4781059050f548dd7e2621"
notion = Client(auth=NOTION_TOKEN)

# Biến toàn cục để quản lý trạng thái bật/tắt giọng nói
is_voice_feedback_enabled = True  # Mặc định bật

# Hàm tạo trang trong Notion
def create_page(title, content):
    try:
        new_page = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={"title": [{"text": {"content": title}}]},
            children=[{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            }]
        )
        return new_page
    except Exception as e:
        print(f"Error: {e}")
        return None

# Hàm phản hồi bằng giọng nói (nếu bật)
async def respond_with_voice(update: Update, text: str):
    global is_voice_feedback_enabled
    if is_voice_feedback_enabled:
        tts = gTTS(text, lang='vi')
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            tts.save(tmp_file.name + '.mp3')
            await update.message.reply_voice(voice=open(tmp_file.name + '.mp3', 'rb'))
    else:
        await update.message.reply_text(text)

# Lệnh bật/tắt giọng nói phản hồi
async def toggle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_voice_feedback_enabled
    is_voice_feedback_enabled = not is_voice_feedback_enabled
    status = "bật" if is_voice_feedback_enabled else "tắt"
    await update.message.reply_text(f"Giọng nói phản hồi đã được {status}.")

# Lệnh /add để thêm công việc bằng tay
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    task = " ".join(context.args)  # Lấy nội dung người dùng gửi
    if task:
        page = create_page(task, "Đây là công việc mới")
        if page:
            await respond_with_voice(update, f"Đã thêm công việc: {task}")
        else:
            await update.message.reply_text("Không thể thêm công việc.")
    else:
        await update.message.reply_text("Vui lòng nhập nội dung công việc sau lệnh /add.")

# Hàm nhận diện giọng nói và gửi phản hồi bằng giọng nói
async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Lấy tệp âm thanh từ người dùng
    voice_file = await update.message.voice.get_file()
    voice_file.download("voice_message.ogg")

    # Sử dụng thư viện SpeechRecognition để chuyển giọng nói thành văn bản
    recognizer = sr.Recognizer()
    with sr.AudioFile("voice_message.ogg") as source:
        audio = recognizer.record(source)

    try:
        # Nhận diện giọng nói và chuyển thành văn bản
        text = recognizer.recognize_google(audio, language="vi-VN")
        page = create_page(text, "Đây là nội dung ghi nhận từ giọng nói")
        if page:
            await respond_with_voice(update, f"Đã tạo công việc: {text}")
        else:
            await update.message.reply_text("Không thể thêm công việc.")
    except sr.UnknownValueError:
        await update.message.reply_text("Không thể nhận diện giọng nói. Vui lòng thử lại.")
    except sr.RequestError:
        await update.message.reply_text("Lỗi kết nối với dịch vụ nhận diện giọng nói.")

# Lệnh /start khi bot khởi động
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Xin chào {update.effective_user.first_name}! Tôi là trợ lý của bạn.")

# Thêm handler vào application
application = ApplicationBuilder().token("7595997674:AAFjioz3MM7sd_q1-K2K2CbEzmEWIjpoHBI").build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_task))
application.add_handler(CommandHandler("toggle_voice", toggle_voice))
application.add_handler(MessageHandler(filters.VOICE, voice_command))

if __name__ == "__main__":
    print("Bot đang chạy... Nhấn Ctrl+C để dừng.")
    application.run_polling()
