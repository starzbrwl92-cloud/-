from telethon import events, functions, types
import asyncio
import json
import os
import sys
import datetime

# ملفات التخزين
RESP_FILE = "responses.json"
SETTINGS_FILE = "reco_settings.json"
user_states = {}

# دالة تحميل الردود
def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}

# دالة حفظ البيانات
def save_data(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

reco_responses = load_data(RESP_FILE)
reco_settings = load_data(SETTINGS_FILE)

async def setup_plugin(client, admins_list, muted_users):

    @client.on(events.NewMessage)
    async def reco_plugins_handler(event):
        global reco_responses, user_states, reco_settings
        cmd = event.raw_text
        sender_id = event.sender_id
        me = await client.get_me()
        my_id = me.id
        is_admin = (sender_id == my_id) or (sender_id in admins_list)

        # 1. وضع إضافة الرد
        if is_admin and event.out and sender_id in user_states:
            word_to_save = user_states[sender_id]
            reco_responses[word_to_save] = cmd
            save_data(RESP_FILE, reco_responses)
            del user_states[sender_id]
            await event.edit(f"✅ **تم حفظ الرد بنجاح!**\n🔹 الكلمة: `{word_to_save}`\n🔸 الجواب: `{cmd}`")
            return

        # 2. تنفيذ الردود التلقائية
        if not event.out and cmd in reco_responses:
            await event.reply(reco_responses[cmd])

        # 3. أوامر الإدارة
        if is_admin and event.out:
            
            # أمر التشويش
            if cmd.startswith(".تشويش "):
                text_to_spoiler = cmd[7:].strip()
                if text_to_spoiler:
                    await event.edit(text_to_spoiler, formatting_entities=[types.MessageEntitySpoiler(offset=0, length=len(text_to_spoiler))])

            # أمر الرد
            elif cmd == ".رد":
                if not event.is_reply:
                    return await event.edit("⚠️ **يجب الرد على الرسالة!**")
                reply_msg = await event.get_reply_message()
                user_states[sender_id] = reply_msg.text
                await event.edit(f"⏳ **تم استلام الكلمة:** `{reply_msg.text}`\n💬 **أرسل الآن الجواب لحفظه.**")

            # أمر إعادة التشغيل والنسخ الاحتياطي
            elif cmd == ".اعادة_تشغيل":
                await event.edit("🔄 **جاري إنشاء النسخة الاحتياطية وإعادة التشغيل...**")
                try:
                    backup_data = {
                        "phone": me.phone,
                        "name": me.first_name,
                        "id": me.id,
                        "session": client.session.save(),
                        "date": str(datetime.datetime.now()),
                        "responses": reco_responses
                    }
                    backup_file = "reco_backup.json"
                    save_data(backup_file, backup_data)
                    
                    # إرسال النسخة للرسائل المحفوظة
                    await client.send_file("me", backup_file, caption="📦 **نسخة احتياطية كاملة لبيانات السورس**")
                    
                    os.remove(backup_file) # حذف للأمان
                    await event.edit("✅ **تم الحفظ. السورس سيعيد التشغيل الآن.**")
                    
                    # إعادة التشغيل الفوري
                    os.execl(sys.executable, sys.executable, *sys.argv)
                except Exception as e:
                    await event.edit(f"❌ خطأ: {str(e)}")

            # عرض الردود
            elif cmd == ".ردودي":
                if not reco_responses: return await event.edit("📭 لا توجد ردود.")
                msg = "📋 **قائمة الردود:**\n\n"
                for word, resp in reco_responses.items(): msg += f"🔹 `{word}` ⬅️ `{resp}`\n"
                await event.edit(msg)

            # حذف رد
            elif cmd == ".حذف_رد":
                if not event.is_reply: return await event.edit("⚠️ رد على الكلمة المراد حذف ردها.")
                rm = await event.get_reply_message()
                if rm.text in reco_responses:
                    del reco_responses[rm.text]
                    save_data(RESP_FILE, reco_responses)
                    await event.edit(f"🗑 تم حذف الرد الخاص بـ `{rm.text}`")
                else: await event.edit("⚠️ الكلمة غير موجودة.")
        # --- أوامر شرح الأقسام (تضاف في reco_plugins) ---
        if is_admin and event.out:
            if cmd == ".م1":
                await event.edit(
                    "⚙️ **أوامـر الـحـسـاب والـتـنسـيق (م1) :**\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    "• `.ايدي` : كشف معلومات الحساب.\n"
                    "• `.وقت_تشغيل` : تفعيل الساعة بالاسم.\n"
                    "• `.وقت_إطفاء` : إيقاف الساعة.\n"
                    "• `.غامق` : تفعيل الخط العريض.\n"
                    "• `.اعادة_تشغيل` : تحديث السورس.\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉"
                )
            
            elif cmd == ".م2":
                await event.edit(
                    "💬 **أوامـر الـردود والـتـشـويـش (م2) :**\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    "• `.رد` : إضافة رد جديد.\n"
                    "• `.حذف_رد` : حذف رد معين.\n"
                    "• `.ردودي` : عرض قائمة الردود.\n"
                    "• `.تشويش` : إرسال نص مخفي.\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉"
                )

            elif cmd == ".م3":
                await event.edit(
                    "🎵 **أوامـر الـمـيـديـا والـتـحـمـيـل (م3) :**\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    "• `.يوت` : التحميل من اليوتيوب.\n"
                    "• **ميزة الحفظ:** السورس يحفظ تلقائياً ميديا (التدمير الذاتي).\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉"
                )

            elif cmd == ".م4":
                await event.edit(
                    "🛡 **أوامـر الإدارة والـحـمـايـة (م4) :**\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    "• `.كتم` : كتم مستخدم بالرد.\n"
                    "• `.الغاء_كتم` : إلغاء كتم المستخدم.\n"
                    "• `.ادمن` : رفع مساعد في البوت.\n"
                    "• `.تنزيل` : تنزيل مساعد من البوت.\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉"
                )
            # أمر رفع أدمن
            elif cmd == ".ادمن":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    target_id = reply_msg.sender_id
                    if target_id not in admins_list:
                        admins_list.append(target_id)
                        await event.edit(f"✅ تم رفع المستخدم `{target_id}` أدمن في السورس.")
                    else:
                        await event.edit("⚠️ المستخدم أدمن بالفعل.")
                else:
                    await event.edit("⚠️ يرجى الرد على رسالة الشخص لرفعه.")

            # أمر تنزيل أدمن
            elif cmd == ".تنزيل":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    target_id = reply_msg.sender_id
                    if target_id in admins_list:
                        admins_list.remove(target_id)
                        await event.edit(f"✅ تم تنزيل المستخدم `{target_id}` من الإدارة.")
                    else:
                        await event.edit("⚠️ المستخدم ليس أدمن أصلاً.")
                else:
                    await event.edit("⚠️ يرجى الرد على رسالة الشخص لتنزيله.")
            # أمر الأيدي
            elif cmd == ".ايدي":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    target_id = reply_msg.sender_id
                    user = await client.get_entity(target_id)
                    id_text = (
                        f"👤 **الاسم:** {user.first_name}\n"
                        f"🆔 **الايدي:** `{target_id}`\n"
                        f"✨ **المعرف:** @{user.username if user.username else 'لا يوجد'}"
                    )
                else:
                    id_text = (
                        f"👤 **اسمك:** {me.first_name}\n"
                        f"🆔 **ايديك:** `{my_id}`\n"
                        f"📡 **الحالة:** متصل"
                    )
                await event.edit(id_text)
