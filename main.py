import os
import json
import logging
import http.server
import socketserver
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# رمز البوت - ضع توكن البوت هنا
BOT_TOKEN = "8133183633:AAEy5gWPk-Xx9XrKRFIiJZ9xJG5YGc5vRhI"

# حالات المحادثة
(MAIN_MENU, CHOOSING_ADD_TYPE, CHOOSING_CATEGORY, ADDING_CATEGORY, 
 ADDING_TITLE, ADDING_TEXT, CHOOSING_PRIORITY, CHOOSING_REMINDER_TYPE,
 CHOOSING_DAY, CHOOSING_HOUR, CHOOSING_MINUTE_GROUP, CHOOSING_EXACT_MINUTE,
 CHOOSING_EDIT_TYPE, EDITING_NOTE, SEARCHING_NOTES) = range(15)

class NotesManager:
    """إدارة الملاحظات والبيانات"""
    
    def __init__(self):
        self.data_file = "notes_data.json"
        self.data = self.load_data()
    
    def load_data(self) -> dict:
        """تحميل البيانات من الملف"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "categories": ["عام", "مهام", "أفكار"],
                    "notes": [],
                    "reminders": []
                }
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")
            return {
                "categories": ["عام", "مهام", "أفكار"],
                "notes": [],
                "reminders": []
            }
    
    def save_data(self):
        """حفظ البيانات في الملف"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
    
    def add_category(self, category_name: str) -> bool:
        """إضافة تصنيف جديد"""
        if category_name not in self.data["categories"]:
            self.data["categories"].append(category_name)
            self.save_data()
            return True
        return False
    
    def add_note(self, title: str, text: str, category: str, priority: str) -> int:
        """إضافة ملاحظة جديدة"""
        note_id = len(self.data["notes"]) + 1
        note = {
            "id": note_id,
            "title": title,
            "text": text,
            "category": category,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.data["notes"].append(note)
        self.save_data()
        return note_id
    
    def get_notes_by_category(self, category: str) -> List[dict]:
        """الحصول على الملاحظات حسب التصنيف"""
        return [note for note in self.data["notes"] if note["category"] == category]
    
    def get_all_notes(self) -> List[dict]:
        """الحصول على جميع الملاحظات"""
        return self.data["notes"]
    
    def search_notes(self, query: str) -> List[dict]:
        """البحث في الملاحظات"""
        query = query.lower()
        results = []
        for note in self.data["notes"]:
            if (query in note["title"].lower() or 
                query in note["text"].lower() or 
                query in note["category"].lower()):
                results.append(note)
        return results
    
    def delete_note(self, note_id: int) -> bool:
        """حذف ملاحظة"""
        for i, note in enumerate(self.data["notes"]):
            if note["id"] == note_id:
                del self.data["notes"][i]
                self.save_data()
                return True
        return False
    
    def update_note(self, note_id: int, **kwargs) -> bool:
        """تحديث ملاحظة"""
        for note in self.data["notes"]:
            if note["id"] == note_id:
                for key, value in kwargs.items():
                    if key in note:
                        note[key] = value
                note["updated_at"] = datetime.now().isoformat()
                self.save_data()
                return True
        return False
    
    def get_note_by_id(self, note_id: int) -> Optional[dict]:
        """الحصول على ملاحظة بواسطة ID"""
        for note in self.data["notes"]:
            if note["id"] == note_id:
                return note
        return None
    
    def delete_category(self, category: str) -> bool:
        """حذف تصنيف"""
        if category in self.data["categories"]:
            self.data["categories"].remove(category)
            # نقل الملاحظات لتصنيف "عام"
            for note in self.data["notes"]:
                if note["category"] == category:
                    note["category"] = "عام"
            self.save_data()
            return True
        return False
    
    def update_category_name(self, old_name: str, new_name: str) -> bool:
        """تحديث اسم التصنيف"""
        if old_name in self.data["categories"] and new_name not in self.data["categories"]:
            # تحديث اسم التصنيف
            index = self.data["categories"].index(old_name)
            self.data["categories"][index] = new_name
            
            # تحديث الملاحظات
            for note in self.data["notes"]:
                if note["category"] == old_name:
                    note["category"] = new_name
            
            self.save_data()
            return True
        return False
    
    def get_stats(self) -> dict:
        """الحصول على إحصائيات الملاحظات"""
        stats = {
            "total_notes": len(self.data["notes"]),
            "total_categories": len(self.data["categories"]),
            "categories_breakdown": {},
            "priority_breakdown": {"🔴": 0, "🟡": 0, "🟢": 0},
            "recent_notes": 0
        }
        
        # إحصائيات التصنيفات
        for category in self.data["categories"]:
            stats["categories_breakdown"][category] = len(self.get_notes_by_category(category))
        
        # إحصائيات الأولويات
        for note in self.data["notes"]:
            priority = note.get("priority", "🟢")
            if priority in stats["priority_breakdown"]:
                stats["priority_breakdown"][priority] += 1
        
        # الملاحظات الحديثة (آخر 7 أيام)
        week_ago = datetime.now() - timedelta(days=7)
        for note in self.data["notes"]:
            try:
                created_at = datetime.fromisoformat(note["created_at"])
                if created_at >= week_ago:
                    stats["recent_notes"] += 1
            except:
                continue
        
        return stats

# إنشاء مدير الملاحظات
notes_manager = NotesManager()

def get_priority_emoji(priority: str) -> str:
    """الحصول على رمز الأولوية"""
    priorities = {"مهم جداً": "🔴", "مهم": "🟡", "عادي": "🟢"}
    return priorities.get(priority, "🟢")

def format_note_preview(note: dict) -> str:
    """تنسيق معاينة الملاحظة"""
    priority = get_priority_emoji(note.get("priority", "عادي"))
    title = note["title"]
    text = note["text"]
    
    # أخذ أول 30 حرف من النص
    preview = text[:30] + "..." if len(text) > 30 else text
    
    return f"{priority} {title} - {preview}"

def create_categories_keyboard(include_add_new: bool = True) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح التصنيفات"""
    keyboard = []
    categories = notes_manager.data["categories"]
    
    # إضافة التصنيفات في صفوف
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                category = categories[i + j]
                row.append(InlineKeyboardButton(
                    f"📁 {category}", 
                    callback_data=f"select_category_{category}"
                ))
        keyboard.append(row)
    
    # إضافة زر إنشاء تصنيف جديد
    if include_add_new:
        keyboard.append([InlineKeyboardButton(
            "➕ إضافة تصنيف جديد", 
            callback_data="add_new_category"
        )])
    
    # زر الإلغاء
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def create_priority_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح الأولويات"""
    keyboard = [
        [InlineKeyboardButton("🔴 مهم جداً", callback_data="priority_مهم جداً")],
        [InlineKeyboardButton("🟡 مهم", callback_data="priority_مهم")],
        [InlineKeyboardButton("🟢 عادي", callback_data="priority_عادي")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_reminder_type_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح نوع التذكير"""
    keyboard = [
        [
            InlineKeyboardButton("⏰ بعد 30 دقيقة", callback_data="reminder_30m"),
            InlineKeyboardButton("⏰ بعد ساعة", callback_data="reminder_1h")
        ],
        [
            InlineKeyboardButton("⏰ بعد ساعتين", callback_data="reminder_2h"),
            InlineKeyboardButton("⏰ بعد 6 ساعات", callback_data="reminder_6h")
        ],
        [
            InlineKeyboardButton("📅 غداً 9 صباحاً", callback_data="reminder_tomorrow_9am"),
            InlineKeyboardButton("📅 غداً 6 مساءً", callback_data="reminder_tomorrow_6pm")
        ],
        [InlineKeyboardButton("🕐 تحديد وقت مخصص", callback_data="reminder_custom")],
        [
            InlineKeyboardButton("🚫 بدون تذكير", callback_data="reminder_none"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_day_selection_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح اختيار اليوم"""
    keyboard = [
        [
            InlineKeyboardButton("📅 اليوم", callback_data="day_today"),
            InlineKeyboardButton("📅 غداً", callback_data="day_tomorrow")
        ],
        [
            InlineKeyboardButton("📅 بعد غد", callback_data="day_after_tomorrow"),
            InlineKeyboardButton("📅 الأسبوع القادم", callback_data="day_next_week")
        ],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_hour_selection_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح اختيار الساعة"""
    keyboard = []
    
    # ساعات من 6 صباحاً إلى 11 مساءً
    hours = list(range(6, 24)) + list(range(0, 6))
    
    for i in range(0, len(hours), 4):
        row = []
        for j in range(4):
            if i + j < len(hours):
                hour = hours[i + j]
                display_hour = f"{hour:02d}:00"
                row.append(InlineKeyboardButton(
                    f"🕐 {display_hour}", 
                    callback_data=f"hour_{hour}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def create_minute_group_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح مجموعات الدقائق"""
    keyboard = [
        [
            InlineKeyboardButton("0️⃣ 00-09", callback_data="minute_group_0"),
            InlineKeyboardButton("1️⃣ 10-19", callback_data="minute_group_1")
        ],
        [
            InlineKeyboardButton("2️⃣ 20-29", callback_data="minute_group_2"),
            InlineKeyboardButton("3️⃣ 30-39", callback_data="minute_group_3")
        ],
        [
            InlineKeyboardButton("4️⃣ 40-49", callback_data="minute_group_4"),
            InlineKeyboardButton("5️⃣ 50-59", callback_data="minute_group_5")
        ],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_exact_minute_keyboard(group: int) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح الدقائق الدقيقة"""
    keyboard = []
    start_minute = group * 10
    
    # إضافة الدقائق في صفوف من 5
    for i in range(0, 10, 5):
        row = []
        for j in range(5):
            minute = start_minute + i + j
            if minute < 60:
                row.append(InlineKeyboardButton(
                    f":{minute:02d}", 
                    callback_data=f"exact_minute_{minute}"
                ))
        if row:
            keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def create_edit_type_keyboard() -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح نوع التعديل"""
    keyboard = [
        [InlineKeyboardButton("📁 تعديل التصنيف", callback_data="edit_category")],
        [InlineKeyboardButton("📝 تعديل الملاحظة", callback_data="edit_note")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_notes_list_keyboard(notes: List[dict], page: int = 0) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح قائمة الملاحظات مع التنقل"""
    keyboard = []
    notes_per_page = 5
    start_idx = page * notes_per_page
    end_idx = start_idx + notes_per_page
    
    page_notes = notes[start_idx:end_idx]
    
    for note in page_notes:
        preview = format_note_preview(note)
        keyboard.append([InlineKeyboardButton(
            preview, 
            callback_data=f"select_note_{note['id']}"
        )])
    
    # أزرار التنقل
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{page-1}"))
    if end_idx < len(notes):
        nav_row.append(InlineKeyboardButton("➡️ التالي", callback_data=f"page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

def create_note_edit_options_keyboard(note_id: int) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح خيارات تعديل الملاحظة"""
    keyboard = [
        [InlineKeyboardButton("📝 تعديل العنوان", callback_data=f"edit_note_title_{note_id}")],
        [InlineKeyboardButton("📄 تعديل النص", callback_data=f"edit_note_text_{note_id}")],
        [InlineKeyboardButton("🎯 تعديل الأولوية", callback_data=f"edit_note_priority_{note_id}")],
        [InlineKeyboardButton("⏰ تعديل التذكير", callback_data=f"edit_note_reminder_{note_id}")],
        [InlineKeyboardButton("🗑 حذف الملاحظة", callback_data=f"delete_note_{note_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_category_edit_options_keyboard(category: str) -> InlineKeyboardMarkup:
    """إنشاء لوحة مفاتيح خيارات تعديل التصنيف"""
    keyboard = [
        [InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"edit_category_name_{category}")],
        [InlineKeyboardButton("🗑 حذف التصنيف", callback_data=f"delete_category_{category}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# دوال الأوامر الرئيسية

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر البداية - تنشيط البوت"""
    welcome_text = """
🤖 **مرحباً بك في بوت تنظيم الملاحظات!**

أنا هنا لمساعدتك في إدارة ملاحظاتك وتذكيرك بها في الوقت المناسب.

📋 **الأوامر المتاحة:**
• `/add` - إضافة ملاحظة أو تصنيف جديد
• `/notes` - عرض الملاحظات السابقة
• `/edit` - تعديل الملاحظات والتصنيفات
• `/search` - البحث في الملاحظات
• `/stats` - عرض إحصائيات الملاحظات
• `/backup` - نسخة احتياطية من البيانات
• `/menu` - عرض هذه القائمة

✨ **ابدأ بإضافة ملاحظتك الأولى باستخدام** `/add`
    """
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر الإضافة - يسأل نوع الإضافة"""
    keyboard = [
        [InlineKeyboardButton("📝 إضافة ملاحظة", callback_data="add_note")],
        [InlineKeyboardButton("📁 إضافة تصنيف", callback_data="add_category")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "ماذا تريد أن تضيف؟",
        reply_markup=reply_markup
    )
    return CHOOSING_ADD_TYPE

async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر عرض الملاحظات"""
    all_notes = notes_manager.get_all_notes()
    
    if not all_notes:
        await update.message.reply_text("📭 لا توجد ملاحظات حتى الآن.\n\nاستخدم `/add` لإضافة ملاحظة جديدة!")
        return
    
    # تجميع الملاحظات حسب التصنيف
    categories_notes = {}
    for note in all_notes:
        category = note["category"]
        if category not in categories_notes:
            categories_notes[category] = []
        categories_notes[category].append(note)
    
    response = "📚 **ملاحظاتك:**\n\n"
    
    for category, notes in categories_notes.items():
        response += f"📁 **{category}** ({len(notes)} ملاحظة):\n"
        
        # عرض أول 5 ملاحظات من كل تصنيف
        for i, note in enumerate(notes[:5], 1):
            preview = format_note_preview(note)
            response += f"  {i}. {preview}\n"
        
        if len(notes) > 5:
            response += f"  ... و {len(notes) - 5} ملاحظات أخرى\n"
        
        response += "\n"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر التعديل - عرض خيارات التعديل"""
    keyboard = create_edit_type_keyboard()
    
    await update.message.reply_text(
        "ماذا تريد أن تعدل؟",
        reply_markup=keyboard
    )
    return CHOOSING_EDIT_TYPE

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر البحث"""
    await update.message.reply_text(
        "🔍 **البحث في الملاحظات**\n\nاكتب الكلمة أو الجملة التي تريد البحث عنها:"
    )
    return SEARCHING_NOTES

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر الإحصائيات"""
    stats = notes_manager.get_stats()
    
    response = "📊 **إحصائيات الملاحظات:**\n\n"
    response += f"📝 إجمالي الملاحظات: **{stats['total_notes']}**\n"
    response += f"📁 إجمالي التصنيفات: **{stats['total_categories']}**\n"
    response += f"🆕 ملاحظات حديثة (آخر 7 أيام): **{stats['recent_notes']}**\n\n"
    
    response += "📁 **تفصيل التصنيفات:**\n"
    for category, count in stats['categories_breakdown'].items():
        response += f"  • {category}: {count} ملاحظة\n"
    
    response += "\n🎯 **تفصيل الأولويات:**\n"
    for priority, count in stats['priority_breakdown'].items():
        priority_text = {"🔴": "مهم جداً", "🟡": "مهم", "🟢": "عادي"}[priority]
        response += f"  {priority} {priority_text}: {count} ملاحظة\n"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر النسخة الاحتياطية"""
    all_notes = notes_manager.get_all_notes()
    
    if not all_notes:
        await update.message.reply_text("📭 لا توجد ملاحظات للنسخ الاحتياطي.")
        return
    
    # تجميع الملاحظات حسب التصنيف
    categories_notes = {}
    for note in all_notes:
        category = note["category"]
        if category not in categories_notes:
            categories_notes[category] = []
        categories_notes[category].append(note)
    
    backup_text = f"=== نسخة احتياطية من ملاحظاتك ===\n"
    backup_text += f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    backup_text += f"إجمالي الملاحظات: {len(all_notes)}\n\n"
    
    for category, notes in categories_notes.items():
        backup_text += f"== تصنيف: {category} ==\n"
        
        for note in notes:
            priority = get_priority_emoji(note.get("priority", "عادي"))
            try:
                created_date = datetime.fromisoformat(note["created_at"]).strftime('%Y-%m-%d')
            except:
                created_date = "غير محدد"
            
            backup_text += f"{priority} {note['title']}\n"
            backup_text += f"   النص: {note['text']}\n"
            backup_text += f"   تاريخ الإنشاء: {created_date}\n\n"
        
        backup_text += "\n"
    
    # إرسال النسخة الاحتياطية كملف نصي
    try:
        with open("backup.txt", "w", encoding="utf-8") as f:
            f.write(backup_text)
        
        with open("backup.txt", "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"notes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption="💾 **نسخة احتياطية من ملاحظاتك**\n\nاحتفظ بهذا الملف في مكان آمن!"
            )
        
        # حذف الملف المؤقت
        os.remove("backup.txt")
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء النسخة الاحتياطية.")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر القائمة"""
    menu_text = """
📋 **قائمة الأوامر:**

🚀 `/start` - تنشيط البوت والترحيب
➕ `/add` - إضافة ملاحظة أو تصنيف جديد
📚 `/notes` - عرض الملاحظات السابقة
✏️ `/edit` - تعديل الملاحظات والتصنيفات
🔍 `/search` - البحث في الملاحظات
📊 `/stats` - عرض إحصائيات الملاحظات
💾 `/backup` - نسخة احتياطية من البيانات
📋 `/menu` - عرض هذه القائمة

💡 **نصيحة:** استخدم الأزرار التفاعلية لسهولة الاستخدام!
    """
    
    await update.message.reply_text(menu_text, parse_mode='Markdown')

# معالجات الأزرار والمحادثات

async def handle_add_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار نوع الإضافة"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_note":
        # بدء إضافة ملاحظة
        keyboard = create_categories_keyboard()
        await query.edit_message_text(
            "📝 **إضافة ملاحظة جديدة**\n\nاختر التصنيف:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CHOOSING_CATEGORY
    
    elif query.data == "add_category":
        # بدء إضافة تصنيف
        await query.edit_message_text(
            "📁 **إضافة تصنيف جديد**\n\nاكتب اسم التصنيف الجديد:"
        )
        return ADDING_CATEGORY
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار التصنيف"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_new_category":
        await query.edit_message_text(
            "📁 **إضافة تصنيف جديد**\n\nاكتب اسم التصنيف الجديد:"
        )
        return ADDING_CATEGORY
    
    elif query.data.startswith("select_category_"):
        category = query.data.replace("select_category_", "")
        context.user_data['selected_category'] = category
        
        await query.edit_message_text(
            f"📝 **إضافة ملاحظة في تصنيف: {category}**\n\nاكتب عنوان الملاحظة:"
        )
        return ADDING_TITLE
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_adding_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إضافة تصنيف جديد"""
    category_name = update.message.text.strip()
    
    if not category_name:
        await update.message.reply_text("❌ يرجى كتابة اسم التصنيف.")
        return ADDING_CATEGORY
    
    if notes_manager.add_category(category_name):
        await update.message.reply_text(f"✅ تم إضافة التصنيف '{category_name}' بنجاح!")
    else:
        await update.message.reply_text(f"⚠️ التصنيف '{category_name}' موجود مسبقاً.")
    
    return ConversationHandler.END

async def handle_adding_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إضافة عنوان الملاحظة"""
    title = update.message.text.strip()
    
    if not title:
        await update.message.reply_text("❌ يرجى كتابة عنوان الملاحظة.")
        return ADDING_TITLE
    
    context.user_data['note_title'] = title
    
    await update.message.reply_text(
        f"📄 **عنوان الملاحظة:** {title}\n\nالآن اكتب نص الملاحظة:"
    )
    return ADDING_TEXT

async def handle_adding_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة إضافة نص الملاحظة"""
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("❌ يرجى كتابة نص الملاحظة.")
        return ADDING_TEXT
    
    context.user_data['note_text'] = text
    
    # عرض خيارات الأولوية
    keyboard = create_priority_keyboard()
    await update.message.reply_text(
        "🎯 **اختر أولوية الملاحظة:**",
        reply_markup=keyboard
    )
    return CHOOSING_PRIORITY

async def handle_priority_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الأولوية"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("priority_"):
        priority = query.data.replace("priority_", "")
        context.user_data['note_priority'] = priority
        
        # عرض خيارات التذكير
        keyboard = create_reminder_type_keyboard()
        await query.edit_message_text(
            f"⏰ **اختر نوع التذكير:**\n\n🎯 الأولوية: {get_priority_emoji(priority)} {priority}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CHOOSING_REMINDER_TYPE
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_reminder_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار نوع التذكير"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "reminder_none":
        # حفظ الملاحظة بدون تذكير
        await save_note_final(update, context, None)
        return ConversationHandler.END
    
    elif query.data == "reminder_custom":
        # التذكير المخصص
        keyboard = create_day_selection_keyboard()
        await query.edit_message_text(
            "📅 **تحديد وقت مخصص**\n\nأولاً، اختر اليوم:",
            reply_markup=keyboard
        )
        return CHOOSING_DAY
    
    elif query.data.startswith("reminder_"):
        # التذكير السريع
        reminder_type = query.data.replace("reminder_", "")
        reminder_time = calculate_reminder_time(reminder_type)
        
        if reminder_time:
            context.user_data['reminder_time'] = reminder_time
            await save_note_final(update, context, reminder_time)
        
        return ConversationHandler.END
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_day_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار اليوم"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("day_"):
        day_type = query.data.replace("day_", "")
        context.user_data['selected_day'] = day_type
        
        # عرض اختيار الساعة
        keyboard = create_hour_selection_keyboard()
        await query.edit_message_text(
            f"🕐 **اختر الساعة:**\n\n📅 اليوم المختار: {get_day_text(day_type)}",
            reply_markup=keyboard
        )
        return CHOOSING_HOUR
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_hour_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الساعة"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("hour_"):
        hour = int(query.data.replace("hour_", ""))
        context.user_data['selected_hour'] = hour
        
        # عرض اختيار مجموعة الدقائق
        keyboard = create_minute_group_keyboard()
        await query.edit_message_text(
            f"🕐 **اختر مجموعة الدقائق:**\n\n📅 الوقت: {get_day_text(context.user_data['selected_day'])} الساعة {hour:02d}:XX",
            reply_markup=keyboard
        )
        return CHOOSING_MINUTE_GROUP
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_minute_group_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار مجموعة الدقائق"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("minute_group_"):
        group = int(query.data.replace("minute_group_", ""))
        context.user_data['selected_minute_group'] = group
        
        # عرض اختيار الدقيقة الدقيقة
        keyboard = create_exact_minute_keyboard(group)
        hour = context.user_data['selected_hour']
        await query.edit_message_text(
            f"🎯 **اختر الدقيقة الدقيقة:**\n\n📅 الوقت: {get_day_text(context.user_data['selected_day'])} الساعة {hour:02d}:{group*10:02d}-{group*10+9:02d}",
            reply_markup=keyboard
        )
        return CHOOSING_EXACT_MINUTE
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_exact_minute_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الدقيقة الدقيقة"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("exact_minute_"):
        minute = int(query.data.replace("exact_minute_", ""))
        
        # حساب وقت التذكير النهائي
        day_type = context.user_data['selected_day']
        hour = context.user_data['selected_hour']
        
        reminder_time = calculate_custom_reminder_time(day_type, hour, minute)
        
        if reminder_time:
            context.user_data['reminder_time'] = reminder_time
            
            # عرض معاينة الوقت
            time_text = reminder_time.strftime("%Y-%m-%d %H:%M")
            await query.edit_message_text(
                f"✅ **تم تحديد وقت التذكير:**\n📅 {time_text}\n\n💾 جاري حفظ الملاحظة..."
            )
            
            await save_note_final(update, context, reminder_time)
        
        return ConversationHandler.END
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_edit_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار نوع التعديل"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "edit_category":
        # تعديل التصنيف
        categories = notes_manager.data["categories"]
        if not categories:
            await query.edit_message_text("📁 لا توجد تصنيفات للتعديل.")
            return ConversationHandler.END
        
        keyboard = create_categories_keyboard(include_add_new=False)
        await query.edit_message_text(
            "📁 **تعديل التصنيف**\n\nاختر التصنيف الذي تريد تعديله:",
            reply_markup=keyboard
        )
        context.user_data['edit_type'] = 'category'
        return CHOOSING_CATEGORY
    
    elif query.data == "edit_note":
        # تعديل الملاحظة
        all_notes = notes_manager.get_all_notes()
        if not all_notes:
            await query.edit_message_text("📝 لا توجد ملاحظات للتعديل.")
            return ConversationHandler.END
        
        keyboard = create_notes_list_keyboard(all_notes)
        await query.edit_message_text(
            "📝 **تعديل الملاحظة**\n\nاختر الملاحظة التي تريد تعديلها:",
            reply_markup=keyboard
        )
        context.user_data['edit_type'] = 'note'
        return EDITING_NOTE
    
    elif query.data == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة البحث في الملاحظات"""
    search_query = update.message.text.strip()
    
    if not search_query:
        await update.message.reply_text("❌ يرجى كتابة كلمة للبحث.")
        return SEARCHING_NOTES
    
    results = notes_manager.search_notes(search_query)
    
    if not results:
        await update.message.reply_text(f"🔍 لم يتم العثور على نتائج لـ: '{search_query}'")
    else:
        response = f"🔍 **نتائج البحث لـ:** '{search_query}'\n"
        response += f"**عدد النتائج:** {len(results)}\n\n"
        
        for i, note in enumerate(results[:10], 1):  # عرض أول 10 نتائج
            preview = format_note_preview(note)
            response += f"{i}. {preview}\n"
            response += f"   📁 التصنيف: {note['category']}\n\n"
        
        if len(results) > 10:
            response += f"... و {len(results) - 10} نتائج أخرى\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    return ConversationHandler.END

# دوال مساعدة

def calculate_reminder_time(reminder_type: str) -> Optional[datetime]:
    """حساب وقت التذكير حسب النوع"""
    now = datetime.now()
    
    if reminder_type == "30m":
        return now + timedelta(minutes=30)
    elif reminder_type == "1h":
        return now + timedelta(hours=1)
    elif reminder_type == "2h":
        return now + timedelta(hours=2)
    elif reminder_type == "6h":
        return now + timedelta(hours=6)
    elif reminder_type == "tomorrow_9am":
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    elif reminder_type == "tomorrow_6pm":
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
    
    return None

def calculate_custom_reminder_time(day_type: str, hour: int, minute: int) -> Optional[datetime]:
    """حساب وقت التذكير المخصص"""
    now = datetime.now()
    
    if day_type == "today":
        target_date = now
    elif day_type == "tomorrow":
        target_date = now + timedelta(days=1)
    elif day_type == "after_tomorrow":
        target_date = now + timedelta(days=2)
    elif day_type == "next_week":
        target_date = now + timedelta(days=7)
    else:
        return None
    
    reminder_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # التأكد من أن الوقت في المستقبل
    if reminder_time <= now:
        return None
    
    return reminder_time

def get_day_text(day_type: str) -> str:
    """الحصول على نص اليوم"""
    day_texts = {
        "today": "اليوم",
        "tomorrow": "غداً",
        "after_tomorrow": "بعد غد",
        "next_week": "الأسبوع القادم"
    }
    return day_texts.get(day_type, day_type)

async def save_note_final(update: Update, context: ContextTypes.DEFAULT_TYPE, reminder_time: Optional[datetime]) -> None:
    """حفظ الملاحظة النهائية"""
    try:
        # الحصول على البيانات المحفوظة
        category = context.user_data.get('selected_category')
        title = context.user_data.get('note_title')
        text = context.user_data.get('note_text')
        priority = context.user_data.get('note_priority')
        
        if not all([category, title, text, priority]):
            await update.callback_query.edit_message_text("❌ خطأ في حفظ البيانات.")
            return
        
        # حفظ الملاحظة
        note_id = notes_manager.add_note(title, text, category, priority)
        
        # إعداد التذكير إذا كان مطلوباً
        reminder_text = ""
        if reminder_time:
            # إضافة التذكير (يمكن تطويره لاحقاً)
            reminder_text = f"\n⏰ تذكير: {reminder_time.strftime('%Y-%m-%d %H:%M')}"
        
        # رسالة النجاح
        success_message = f"""
✅ **تم حفظ الملاحظة بنجاح!**

📝 **العنوان:** {title}
📄 **النص:** {text[:50]}{'...' if len(text) > 50 else ''}
📁 **التصنيف:** {category}
🎯 **الأولوية:** {get_priority_emoji(priority)} {priority}{reminder_text}

**رقم الملاحظة:** #{note_id}
        """
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(success_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(success_message, parse_mode='Markdown')
        
        # تنظيف البيانات المؤقتة
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"خطأ في حفظ الملاحظة: {e}")
        error_message = "❌ حدث خطأ أثناء حفظ الملاحظة."
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة"""
    context.user_data.clear()
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ تم الإلغاء.")
    else:
        await update.message.reply_text("❌ تم الإلغاء.")
    
    return ConversationHandler.END

# إعداد الخادم البسيط
def start_web_server():
    """بدء خادم ويب بسيط لـ Render"""
    PORT = int(os.environ.get('PORT', 8000))
    
    class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>Notes Bot is Running!</h1><p>Telegram bot is active and working.</p>')
            elif self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "healthy", "bot": "running"}')
            else:
                self.send_response(404)
                self.end_headers()
    
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        logger.info(f"خادم الويب يعمل على المنفذ {PORT}")
        httpd.serve_forever()

def main():
    """تشغيل البوت"""
    # التأكد من وجود التوكن
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("يرجى وضع توكن البوت في المتغير BOT_TOKEN")
        return
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إعداد معالج المحادثة للإضافة
    add_conversation = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            CHOOSING_ADD_TYPE: [CallbackQueryHandler(handle_add_type_choice)],
            CHOOSING_CATEGORY: [CallbackQueryHandler(handle_category_choice)],
            ADDING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_adding_category)],
            ADDING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_adding_title)],
            ADDING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_adding_text)],
            CHOOSING_PRIORITY: [CallbackQueryHandler(handle_priority_choice)],
            CHOOSING_REMINDER_TYPE: [CallbackQueryHandler(handle_reminder_type_choice)],
            CHOOSING_DAY: [CallbackQueryHandler(handle_day_choice)],
            CHOOSING_HOUR: [CallbackQueryHandler(handle_hour_choice)],
            CHOOSING_MINUTE_GROUP: [CallbackQueryHandler(handle_minute_group_choice)],
            CHOOSING_EXACT_MINUTE: [CallbackQueryHandler(handle_exact_minute_choice)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cancel$"),
            CommandHandler("cancel", cancel_conversation)
        ]
    )
    
    # إعداد معالج المحادثة للتعديل
    edit_conversation = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_command)],
        states={
            CHOOSING_EDIT_TYPE: [CallbackQueryHandler(handle_edit_type_choice)],
            EDITING_NOTE: [CallbackQueryHandler(lambda u, c: ConversationHandler.END)]  # مبسط
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cancel$"),
            CommandHandler("cancel", cancel_conversation)
        ]
    )
    
    # إعداد معالج المحادثة للبحث
    search_conversation = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            SEARCHING_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    )
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(add_conversation)
    application.add_handler(edit_conversation)
    application.add_handler(search_conversation)
    application.add_handler(CommandHandler("notes", notes_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("menu", menu_command))
    
    # بدء الخادم في خيط منفصل
    web_server_thread = threading.Thread(target=start_web_server, daemon=True)
    web_server_thread.start()
    
    # بدء البوت
    logger.info("🤖 بوت تنظيم الملاحظات يعمل الآن...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main() 
