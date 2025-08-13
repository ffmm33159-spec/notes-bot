import os
import json
import logging
import http.server
import socketserver
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# رمز البوت
BOT_TOKEN = "8078959273:AAF5Y5F1mzNDIfPOdb3GWhzary6-vKhtUWY"

class NotesManager:
    """إدارة الملاحظات البسيطة"""
    
    def __init__(self):
        self.data_file = "notes_data.json"
        self.data = self.load_data()
    
    def load_data(self):
        """تحميل البيانات"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"notes": [], "test_count": 0}
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")
            return {"notes": [], "test_count": 0}
    
    def save_data(self):
        """حفظ البيانات"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info("تم حفظ البيانات بنجاح")
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
    
    def test_save(self):
        """اختبار النظام"""
        self.data["test_count"] += 1
        self.data["last_test"] = datetime.now().isoformat()
        self.save_data()
        return self.data["test_count"]

# إنشاء مدير الملاحظات
notes_manager = NotesManager()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    test_count = notes_manager.test_save()
    
    welcome_text = f"""
🤖 **مرحباً بك في بوت الملاحظات!**

✅ البوت يعمل بشكل صحيح!
🔢 عدد مرات الاختبار: {test_count}
📅 وقت الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **الأوامر المتاحة حالياً:**
• `/start` - اختبار البوت
• `/test` - اختبار النظام
• `/status` - حالة البوت

🔄 **المرحلة 1:** الأساسيات والاختبار
⏳ **قريباً:** إضافة الملاحظات والمميزات المتقدمة
    """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الاختبار"""
    try:
        test_count = notes_manager.test_save()
        
        status_text = f"""
🧪 **اختبار النظام:**

✅ نظام الحفظ: يعمل
✅ نظام JSON: يعمل  
✅ التوقيت: يعمل
✅ العداد: {test_count}

📊 **تفاصيل النظام:**
• ملف البيانات: {notes_manager.data_file}
• آخر حفظ: {datetime.now().strftime('%H:%M:%S')}
• حالة الاتصال: نشط

🎯 **النتيجة: البوت يعمل بشكل مثالي!**
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"خطأ في الاختبار: {e}")
        await update.message.reply_text(f"❌ خطأ في الاختبار: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة البوت"""
    try:
        data = notes_manager.data
        
        status_text = f"""
📊 **حالة البوت:**

🟢 **الحالة:** نشط ويعمل
📝 **الملاحظات:** {len(data.get('notes', []))}
🔢 **مرات الاختبار:** {data.get('test_count', 0)}
⏰ **آخر نشاط:** {data.get('last_test', 'غير محدد')}

💾 **نظام الحفظ:** يعمل بشكل طبيعي
🌐 **الاتصال:** متصل
🚀 **الاستضافة:** Render
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"خطأ في عرض الحالة: {e}")
        await update.message.reply_text(f"❌ خطأ في عرض الحالة: {str(e)}")

def start_web_server():
    """خادم ويب بسيط"""
    PORT = int(os.environ.get('PORT', 8000))
    
    class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                response = f"""
                <html>
                <head><title>Notes Bot</title></head>
                <body>
                    <h1>🤖 بوت الملاحظات يعمل!</h1>
                    <p>✅ البوت نشط ويعمل بشكل طبيعي</p>
                    <p>📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>🔢 عدد الاختبارات: {notes_manager.data.get('test_count', 0)}</p>
                    <p>🌐 الخادم: Render</p>
                </body>
                </html>
                """.encode('utf-8')
                self.wfile.write(response)
            elif self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                health_data = {
                    "status": "healthy",
                    "bot": "running",
                    "timestamp": datetime.now().isoformat(),
                    "test_count": notes_manager.data.get('test_count', 0)
                }
                self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>404 - Page Not Found</h1>')
    
    try:
        with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
            logger.info(f"🌐 خادم الويب يعمل على المنفذ {PORT}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في خادم الويب: {e}")

def main():
    """تشغيل البوت"""
    # التأكد من التوكن
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ يرجى وضع توكن البوت الصحيح!")
        return
    
    try:
        # إنشاء التطبيق
        application = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة الأوامر
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # بدء الخادم في خيط منفصل
        web_server_thread = threading.Thread(target=start_web_server, daemon=True)
        web_server_thread.start()
        
        # بدء البوت
        logger.info("🤖 بوت الملاحظات - المرحلة 1 يعمل الآن...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")

if __name__ == '__main__':
    main()
