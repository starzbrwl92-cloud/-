from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.messages import CreateChatRequest, EditChatPhotoRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, InputChatUploadedPhoto
import asyncio, os, time, pytz, re, importlib.util, sys
import yt_dlp
from datetime import datetime, timedelta

# --- الأرقام والخطوط المزخرفة المطورة لـ سورس ريكو ---
fonts = {
    "0":"0️⃣", "1":"1️⃣", "2":"2️⃣", "3":"3️⃣", "4":"4️⃣",
    "5":"5️⃣", "6":"6️⃣", "7":"7️⃣", "8":"8️⃣", "9":"9️⃣",
    ":":":", "A":"𝔸", "P":"ℙ", "M":"𝕄"
}

def get_styled_time(t_str):
    return "".join(fonts.get(c, c) for c in t_str.upper())

async def start_user_source(session_str, api_id, api_hash, install_info=None):
    client = TelegramClient(StringSession(session_str), api_id, api_hash)
    
    # --- متغيرات التحكم الأساسية ---
    save_enabled = True
    bold_enabled = False 
    storage_pv = None    
    storage_groups = None 
    storage_deleted = None 
    name_task = None 
    original_name = "" 
    DEV_USER = "@I_QQ_Q"
    SOURCE_CH = "SORS_RECO"
    
    # قائمة الإدمنية المرفوعين بالبوت
    admins_list = []
    
    # قائمة المستخدمين المكتومين
    muted_users = []
    
    # مخزن الرسائل المحذوفة (الكاش) لضمان الاستعادة
    msg_cache = {}

    # --- وظيفة تحديث الوقت في الاسم تلقائياً ---
    async def auto_update_name():
        nonlocal original_name
        try:
            me = await client.get_me()
            if not original_name or "|" in original_name:
                original_name = me.first_name.split('|')[0].strip()
        except Exception as e: 
            print(f"Error fetching profile for time: {e}")
            original_name = "User"

        while True:
            try:
                tz = pytz.timezone('Asia/Baghdad')
                time_now_str = datetime.now(tz).strftime("%I:%M %p")
                styled_time = get_styled_time(time_now_str)
                await client(functions.account.UpdateProfileRequest(
                    first_name=f"{original_name} | {styled_time}"
                ))
                await asyncio.sleep(60) 
            except asyncio.CancelledError: 
                break
            except Exception as e: 
                print(f"Error updating name clock: {e}")
                await asyncio.sleep(10)

    # --- وظيفة تعيين صورة البروفايل للمجموعة من ملف محلي ---
    async def set_storage_photo(chat_id, file_name):
        if os.path.exists(file_name):
            try:
                # رفع الملف أولاً إلى سيرفرات تليجرام
                uploaded_file = await client.upload_file(file_name)
                # تعيين الملف المرفوع كصورة للمجموعة
                await client(EditChatPhotoRequest(
                    chat_id=chat_id,
                    photo=InputChatUploadedPhoto(uploaded_file)
                ))
                print(f"✅ تم تعيين الصورة {file_name} بنجاح.")
                return True
            except Exception as e:
                print(f"❌ فشل تعيين الصورة {file_name}: {e}")
        else:
            print(f"⚠️ الملف {file_name} غير موجود في المجلد.")
        return False

    # --- وظيفة إنشاء وجلب أيدي التخزين ---
    async def create_storage_group(title, photo_file, description):
        try:
            # البحث أولاً إذا كانت المجموعة موجودة مسبقاً
            async for dialog in client.iter_dialogs(limit=100):
                if dialog.name == title: 
                    return dialog.id
            
            # إنشاء المجموعة إذا لم تكن موجودة
            result = await client(CreateChatRequest(title=title, users=["me"]))
            
            chat_id = None
            try:
                if hasattr(result, 'chats') and result.chats:
                    chat_id = result.chats[0].id
                elif hasattr(result, 'updates') and hasattr(result.updates, 'updates'):
                    for u in result.updates.updates:
                        if hasattr(u, 'message') and hasattr(u.message, 'peer_id') and hasattr(u.message.peer_id, 'chat_id'):
                            chat_id = u.message.peer_id.chat_id
                            break
            except: pass

            if not chat_id:
                await asyncio.sleep(3)
                async for dialog in client.iter_dialogs(limit=20):
                    if dialog.name == title:
                        chat_id = dialog.id
                        break

            if chat_id:
                await asyncio.sleep(2) # انتظار لضمان استقرار المجموعة
                
                # رفع الصورة المحلية (ka, am, ma)
                await set_storage_photo(chat_id, photo_file)
                
                # إرسال رسالة الترحيب
                await client.send_message(chat_id, description)
                return chat_id
                
            return None
        except Exception as e:
            print(f"❌ خطأ إنشاء المجموعة {title}: {e}")
            return None
        # معالجة الخط الغامق التلقائي
        if event.out and bold_enabled and event.text:
            if not event.text.startswith("."): # لكي لا يخرب الأوامر
                new_text = f"**{event.text}**"
                if event.text != new_text:
                    await event.edit(new_text)

    # --- إعداد القنوات ومجموعات التخزين عند التشغيل ---
    async def setup_all_storages():
        nonlocal storage_pv, storage_groups, storage_deleted
        try: 
            await client(JoinChannelRequest(SOURCE_CH))
        except: 
            pass

        async for dialog in client.iter_dialogs(limit=100):
            if dialog.name == "RECO PV STORAGE": 
                storage_pv = dialog.id
            elif dialog.name == "RECO GROUPS STORAGE": 
                storage_groups = dialog.id
            elif dialog.name == "RECO DELETED STORAGE": 
                storage_deleted = dialog.id
        
        # إنشاء المجموعات باستخدام صورك المحلية المحددة
        if not storage_pv: 
            storage_pv = await create_storage_group(
                "RECO PV STORAGE", 
                "ka.jpg", 
                "✅ **تم تعيين صورة التخزين الخاص بنجاح**\n\n📂 **RECO PV STORAGE**\nهذه المجموعة مخصصة لتخزين رسائل الخاص والميديا ذاتية التدمير."
            )
        if not storage_groups: 
            storage_groups = await create_storage_group(
                "RECO GROUPS STORAGE", 
                "am.jpg", 
                "✅ **تم تعيين صورة تخزين المجموعات بنجاح**\n\n👥 **RECO GROUPS STORAGE**\nهذه المجموعة مخصصة لتخزين رسائل المجموعات."
            )
        if not storage_deleted: 
            storage_deleted = await create_storage_group(
                "RECO DELETED STORAGE", 
                "ma.jpg", 
                "✅ **تم تعيين صورة أرشيف المحذوفات بنجاح**\n\n🗑 **RECO DELETED STORAGE**\nهنا يتم حفظ أي رسالة يتم حذفها."
            )

    # --- تنظيف الكاش بشكل دوري للرسائل القديمة ---
    async def cache_cleaner():
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            to_delete = [m_id for m_id, data in msg_cache.items() if now > data['expiry']]
            for m_id in to_delete:
                msg_cache.pop(m_id, None)

    # --- معالج الرسائل الرئيسي ---
    @client.on(events.NewMessage)
    async def main_handler(event):
        nonlocal save_enabled, name_task, original_name, bold_enabled, admins_list, muted_users
        
        sender_id = event.sender_id
        try:
            me = await client.get_me()
            my_id = me.id
        except: return
        
        # التحقق من الرتبة
        is_admin = (sender_id == my_id) or (sender_id in admins_list)

        # حذف رسائل المكتومين
        if sender_id in muted_users and not event.out:
            try:
                if event.is_private:
                    await event.delete()
                elif event.is_group:
                    permissions = await client.get_permissions(event.chat_id, me.id)
                    if permissions.is_admin or permissions.is_creator:
                        await event.delete()
            except: pass

        # تخزين الرسائل لكشف المحذوفات
        if event.is_private and not event.out:
            msg_cache[event.id] = {
                'message': event.message,
                'expiry': datetime.now() + timedelta(minutes=10)
            }

        # --- معالجة الأوامر ---
                        # --- بداية قسم الأوامر المعدل ---
        if is_admin:
            cmd = event.raw_text

            # أمر الأيدي
            if cmd == ".ايدي":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    user = await client.get_entity(reply_msg.sender_id)
                    id_text = f"👤 **الاسم:** {user.first_name}\n🆔 **الايدي:** `{user.id}`"
                else:
                    id_text = f"👤 **اسمك:** {me.first_name}\n🆔 **ايديك:** `{my_id}`"
                await event.edit(id_text)

            # أمر الكتم
            elif cmd == ".كتم":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    target_id = reply_msg.sender_id
                    if target_id == my_id: 
                        return await event.edit("⚠️ لا يمكنك كتم نفسك.")
                    if target_id not in muted_users:
                        muted_users.append(target_id)
                        await event.edit(f"✅ تم كتم المستخدم (`{target_id}`) بنجاح.")
                    else: 
                        await event.edit("⚠️ المستخدم مكتوم بالفعل.")
                else: 
                    await event.edit("⚠️ يرجى الرد على رسالة الشخص.")

            # أمر إلغاء الكتم
            elif cmd == ".الغاء_كتم":
                if event.is_reply:
                    reply_msg = await event.get_reply_message()
                    target_id = reply_msg.sender_id
                    if target_id in muted_users:
                        muted_users.remove(target_id)
                        await event.edit(f"✅ تم إلغاء كتم المستخدم بنجاح.")
                    else: 
                        await event.edit("⚠️ المستخدم ليس في قائمة الكتم.")
                else:
                    await event.edit("⚠️ يرجى الرد على رسالة الشخص.")

            # أمر اليوتيوب المطور
            elif cmd.startswith(".يوت"):
                query = cmd.split(maxsplit=1)
                if len(query) < 2: 
                    return await event.edit("⚠️ يرجى كتابة اسم الأغنية.")
                
                search_query = query[1]
                status_msg = await event.edit(f"⏳ **جاري البحث والتحميل:** `{search_query}`")

                try:
                    if not os.path.exists('downloads'): 
                        os.makedirs('downloads')
                    
                    ydl_opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio/best',
                        'outtmpl': 'downloads/%(title)s.%(ext)s',
                        'quiet': True, 
                        'default_search': 'ytsearch1',
                        'nocheckcertificate': True
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(search_query, download=True)
                        if 'entries' in info: 
                            info = info['entries'][0]
                        file_path = ydl.prepare_filename(info)
                        filesize = os.path.getsize(file_path) / (1024 * 1024)

                    await status_msg.edit(f"🚀 **جاري رفع الملف...**\n📦 **الحجم:** `{filesize:.1f} MB`")
                    
                    await client.send_file(
                        event.chat_id, 
                        file_path, 
                        caption=f"🎵 **تم التحميل:** `{info['title']}`\n📦 **الحجم:** `{filesize:.1f} MB`", 
                        attributes=[types.DocumentAttributeAudio(
                            duration=int(info.get('duration', 0)), 
                            title=info.get('title'), 
                            performer='RECO'
                        )]
                    )
                    
                    if os.path.exists(file_path): 
                        os.remove(file_path)
                    await status_msg.delete()
                    
                except Exception as e: 
                    await status_msg.edit(f"❌ **حدث خطأ:**\n`{str(e)[:100]}`")
        # --- نهاية قسم الأوامر ---


            elif cmd == ".فحص":
                start_t = time.time()
                tz = pytz.timezone('Asia/Baghdad')
                time_now = datetime.now(tz).strftime("%I:%M:%S %p")
                ping = round((time.time() - start_t) * 1000, 2)
                
                # جلب المتغيرات من config إذا لم تكن معرفة محلياً
                dev_user = "@N_QQ_H" # أو استبدلها بمتغيرك
                source_ch = "SORS_RECO"

                check_text = (
                    f"🛡 **تـقـريـر فـحـص سـورس ريـكـو الـمـطـور :**\n"
                    f"‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    f"👑 **صـاحـب الـحـساب :** [{me.first_name}](tg://user?id={me.id})\n"
                    f"👤 **الـمـرسـل :** [اضـغـط هـنـا](tg://user?id={sender_id})\n"
                    f"📡 **سـرعـة الـبـنـج :** `{ping}ms`\n"
                    f"⏰ **الـوقـت الـآن :** `{time_now}`\n"
                    f"⚙️ **الـحـالـة :** `ACTIVE ✅`\n"
                    f"‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    f"🦅 **- RECO SOURCE IS THE BEST -**\n"
                    f"👨‍💻 **Dev:** {dev_user} | **Channel:** @{source_ch}"
                )
                
                try:
                    # التحقق إذا كانت الصورة موجودة في المجلد
                    photo_path = "f.jpg"
                    if os.path.exists(photo_path):
                        await client.send_message(event.chat_id, check_text, file=photo_path)
                    else:
                        # إذا لم يجد الصورة يرسل النص فقط
                        await client.send_message(event.chat_id, check_text)
                    
                    if event.out: 
                        await event.delete()
                except Exception: 
                    if event.out: await event.edit(check_text)
                    else: await event.reply(check_text)

            elif cmd == ".الاوامر":
                help_main = (
                    "🦅 **قـائـمـة أقـسـام أوامـر ريـكـو**\n"
                    "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
                    "⚙️ أوامـر الـحـسـاب والـتـنـسـيق ⇦ `.م1`\n"
                    "💬 أوامـر الـردود والـتـشـويـش ⇦ `.م2`\n"
                    "🎵 أوامـر الـمـيـديـا والـتـحـمـيل ⇦ `.م3`\n"
                    "🛡 أوامـر الإدارة والـحـمـايـة ⇦ `.م4`"
                )
                await event.edit(help_main)

            elif cmd == ".وقت_تشغيل" and sender_id == my_id:
                if not name_task or name_task.done():
                    name_task = asyncio.create_task(auto_update_name())
                    await event.edit("✅ **تم تفعيل الساعة في الاسم.**")

            elif cmd == ".وقت_إطفاء" and sender_id == my_id:
                if name_task:
                    name_task.cancel()
                    name_task = None
                    await client(functions.account.UpdateProfileRequest(first_name=original_name))
                    await event.edit("📴 **تم إيقاف الساعة.**")

            elif cmd == ".اعادة_تشغيل" and sender_id == my_id:
                await event.edit("♻️ **جاري إعادة التشغيل...**")
                os.execl(sys.executable, sys.executable, *sys.argv)

            elif cmd == ".غامق" and sender_id == my_id:
                bold_enabled = True
                await event.edit("✍️ **تم تفعيل الخط الغامق.**")

        # --- حفظ الميديا وتوجيه الرسائل ---
        if not event.out:
            try:
                if event.is_private:
                    if event.media and hasattr(event.media, 'ttl_seconds') and event.media.ttl_seconds:
                        path = await event.download_media()
                        cap = f"📥 **ميديا ذاتية التدمير من:** `{sender_id}`"
                        if storage_pv: await client.send_message(storage_pv, cap, file=path)
                        await client.send_message("me", cap, file=path)
                        if os.path.exists(path): os.remove(path)
                    elif storage_pv and sender_id not in admins_list:
                        await client.forward_messages(storage_pv, event.message)
                
                elif (event.is_group or event.is_channel) and storage_groups:
                    if event.chat_id not in [storage_pv, storage_groups, storage_deleted]:
                        await client.forward_messages(storage_groups, event.message)
            except: pass

    # --- كاشف المحذوفات ---
    @client.on(events.MessageDeleted)
    async def delete_handler(event):
        for msg_id in event.deleted_ids:
            if msg_id in msg_cache:
                old_msg = msg_cache[msg_id]['message']
                if storage_deleted:
                    sender = await old_msg.get_sender()
                    name = sender.first_name if sender else "مجهول"
                    await client.send_message(storage_deleted, f"🗑 **حذف رسالة من:** {name}")
                    if old_msg.text: await client.send_message(storage_deleted, old_msg.text)
                    if old_msg.media:
                        try:
                            path = await client.download_media(old_msg)
                            await client.send_message(storage_deleted, file=path)
                            if os.path.exists(path): os.remove(path)
                        except: pass
                msg_cache.pop(msg_id, None)

    # تحميل الإضافات
    if os.path.exists("reco_plugins.py"):
        try:
            spec = importlib.util.spec_from_file_location("reco_plugins", "reco_plugins.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'setup_plugin'):
                await module.setup_plugin(client, admins_list, muted_users)
        except Exception as e: print(f"❌ خطأ الإضافات: {e}")

    try:
        await client.start()
        await setup_all_storages()
        asyncio.create_task(cache_cleaner())
        print(f"✅ سـورس ريـكـو يـعـمـل.")
        await client.run_until_disconnected()
    except Exception as e: raise e
