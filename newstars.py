import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- KONFIGURATSIYA ---
TOKEN = "7579301801:AAFRys9U1BKbLOA6u7pZUzUPWy0fo3As_-Y"
ADMIN_ID = 7362457858
ADMIN_USERNAME = "Nobody_ff2"

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("bot_main_data.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        name TEXT, 
        username TEXT, 
        total_stars INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()

init_db()

class OrderProcess(StatesGroup):
    waiting_for_username = State()
    waiting_for_receipt = State()
    waiting_for_broadcast = State()

# --- TUGMALAR ---
def main_menu_reply(user_id):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="💎 Premium"), types.KeyboardButton(text="🌟 Stars"))
    builder.row(types.KeyboardButton(text="👤 Profilim"), types.KeyboardButton(text="👨‍💻 Admin bilan bogʻlanish"))
    
    if user_id == ADMIN_ID:
        builder.row(types.KeyboardButton(text="📊 Statistika"), types.KeyboardButton(text="📢 Reklama tarqatish"))
    
    return builder.as_markup(resize_keyboard=True)

# Command("start") ni biroz kengaytiramiz yoki oddiy xabar sifatida tekshiramiz
@dp.message(F.text.startswith("/start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    user_id = message.from_user.id
    name = message.from_user.full_name
    # Ismdagi maxsus belgilarni HTML uchun xavfsiz qilish
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

    # Bazaga yozish
    try:
        conn = sqlite3.connect("bot_main_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, name, username) VALUES (?, ?, ?)", (user_id, name, username))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Baza xatosi: {e}")

    # Deep linking
    full_text = message.text
    if " " in full_text:
        command_args = full_text.split(maxsplit=1)[1]
        
        if command_args.startswith("order_"):
            parts = command_args.split("_", 2) 
            
            if len(parts) >= 3:
                p_name = parts[1].replace("-", " ") 
                u_target = parts[2]
                
                if not u_target.isdigit() and not u_target.startswith("@"):
                    u_target = f"@{u_target}"

                await state.update_data(product=p_name, target_user=u_target, price="Sayt narxi")
                
                # Markdown o'rniga HTML ishlatamiz (bu juda xavfsiz)
                response_text = (
                    f"✅ <b>Saytdan buyurtma qabul qilindi!</b>\n\n"
                    f"📦 <b>Mahsulot:</b> {p_name}\n"
                    f"👤 <b>Yuboriladigan profil:</b> <code>{u_target}</code>\n\n"
                    f"‼️ Iltimos, to'lov chekini (rasm/skrinshot) shu yerga yuboring."
                )
                await message.answer(response_text, parse_mode="HTML")
                await state.set_state(OrderProcess.waiting_for_receipt)
                return

    # Oddiy start
    await message.answer(
        f"Assalomu alaykum, {safe_name}! 👋\nBotimizga xush kelibsiz.", 
        reply_markup=main_menu_reply(user_id),
        parse_mode="HTML"
    )
# --- PROFIL BO'LIMI ---
@dp.message(F.text == "👤 Profilim")
async def view_profile(message: types.Message):
    conn = sqlite3.connect("bot_main_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT total_stars FROM users WHERE id=?", (message.from_user.id,))
    data = cursor.fetchone()
    conn.close()
    
    stars_count = data[0] if data else 0
    text = (
        f"👤 **Profilingiz ma'lumotlari:**\n\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"🌟 **Jami sotib olingan Stars:** `{stars_count} ta`"
    )
    await message.answer(text, parse_mode="Markdown")

# --- ADMIN STATISTIKA (ID VA HAVOLA BILAN YANGILANDI) ---
@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def admin_stats(message: types.Message):
    conn = sqlite3.connect("bot_main_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, username FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        await message.answer("Hozircha foydalanuvchilar yo'q.")
        return

    text = f"📈 **Bot statistikasi:**\n\nJami: {len(users)} ta foydalanuvchi\n\n"
    text += "👤 **Foydalanuvchilar ro'yxati:**\n"
    
    for row in users:
        u_id = row[0]
        # Ismni HTML xatolaridan tozalash
        u_name = row[1].replace("<", "&lt;").replace(">", "&gt;")
        u_username = row[2]
        # Har bir foydalanuvchi uchun ID va bosish mumkin bo'lgan ism (havola) qo'shildi
        text += f"• <a href='tg://user?id={u_id}'>{u_name}</a> | 🆔 `{u_id}` | {u_username}\n"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await message.answer(text[i:i+4000], parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

# --- ADMIN REKLAMA ---
@dp.message(F.text == "📢 Reklama tarqatish", F.from_user.id == ADMIN_ID)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Reklama xabarini yuboring:")
    await state.set_state(OrderProcess.waiting_for_broadcast)

@dp.message(OrderProcess.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def perform_broadcast(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot_main_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    user_ids = cursor.fetchall()
    conn.close()
    
    count = 0
    for (uid,) in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Xabar {count} ta odamga yuborildi.")
    await state.clear()

# --- PREMIUM VA STARS ---
@dp.message(F.text == "💎 Premium")
async def premium_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔑 Akkga kirish orqali", url=f"https://t.me/{ADMIN_USERNAME}?text=Salom, Menga premium kerak"))
    builder.row(types.InlineKeyboardButton(text="🚫 Akkga kirmasdan", callback_data="prem_no_login"))
    await message.answer("💎 **Premium turini tanlang:**", reply_markup=builder.as_markup())

@dp.message(F.text == "🌟 Stars")
async def stars_menu(message: types.Message):
    prices = {"50": "15.000", "100": "28.000", "250": "60.000", "350": "85.000", "500": "115.000", "750": "175.000", "1000": "235.000"}
    builder = InlineKeyboardBuilder()
    for amount, price in prices.items():
        builder.row(types.InlineKeyboardButton(text=f"🌟 {amount} Stars - {price} so'm", callback_data=f"order_{amount} Stars_{price}"))
    await message.answer("🌟 **Stars narxlari:**", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "prem_no_login")
async def prem_prices_inline(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💎 3 oy - 165.000 so'm", callback_data="order_Premium 3 oy_165.000"))
    builder.row(types.InlineKeyboardButton(text="💎 6 oy - 220.000 so'm", callback_data="order_Premium 6 oy_220.000"))
    builder.row(types.InlineKeyboardButton(text="💎 12 oy - 390.000 so'm", callback_data="order_Premium 12 oy_390.000"))
    await callback.message.edit_text("💎 **Premium narxlari:**", reply_markup=builder.as_markup())

# --- BUYURTMA JARAYONI ---
@dp.callback_query(F.data.startswith("order_"))
async def ask_username(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    await state.update_data(product=data_parts[1], price=data_parts[2])
    await callback.message.answer(f"Siz **{data_parts[1]}**ni tanladingiz.\nBuyurtma yubormoqchi bo'lgan **(@username)**ni yuboring.")
    await state.set_state(OrderProcess.waiting_for_username)

@dp.message(OrderProcess.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    target = message.text if message.text.startswith("@") else f"@{message.text}"
    user_data = await state.get_data()
    await state.update_data(target_user=target)
    payment_text = (
        f"💰 **To'lov miqdori:** {user_data['price']} so'm\n📦 **Mahsulot:** {user_data['product']}\n👤 **Username:** {target}\n\n"
        "💳 **To'lov uchun!:**\n📍 9860-6067-5228-3238\n👤 Karta egasi: X.I.\n📞 Karta: +998-88-855-13-20\n\n"
        "‼️ To'lov qilganingizdan so'ng chekni rasm ko'rinishida yuboring."
    )
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="✅ Toʻlov qildim", callback_data="paid"))
    await message.answer(payment_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "paid")
async def ask_receipt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Iltimos, to'lov chekini (rasm) yuboring:")
    await state.set_state(OrderProcess.waiting_for_receipt)

@dp.message(OrderProcess.waiting_for_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("Toʻlov tekshiruvda, admin tasdiqlashi kutilmoqda...")
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admok_{message.from_user.id}_{data['product']}"))
    builder.add(types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admno_{message.from_user.id}"))
    admin_caption = f"🔔 **Yangi buyurtma!**\n\n📦 **Mahsulot:** {data['product']}\n💰 **Narxi:** {data['price']} so'm\n👤 **Oluvchi:** {data['target_user']}\n🆔 **ID:** `{message.from_user.id}`\n📝 **Xaridor:** @{message.from_user.username}"
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_caption, reply_markup=builder.as_markup())
    await state.clear()

# --- ADMIN TASDIQLASHI ---
@dp.callback_query(F.data.startswith("admok_"))
async def admin_confirm(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id, product = int(parts[1]), parts[2]
    
    if "Stars" in product:
        stars_to_add = int(product.split(" ")[0])
        conn = sqlite3.connect("bot_main_data.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET total_stars = total_stars + ? WHERE id=?", (stars_to_add, user_id))
        conn.commit()
        conn.close()

    await bot.send_message(user_id, f"✅ To'lov tasdiqlandi, buyurtma yuborildi!")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **TASDIQLANDI**")

@dp.callback_query(F.data.startswith("admok_"))
async def admin_confirm(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id, product = int(parts[1]), parts[2]
    
    # Bizga oluvchi (target_user) kerak. Uni admin xabarining caption'idan yoki state'dan olsak bo'ladi.
    # Eng xavfsiz yo'li - caption ichidan qidirish:
    caption = callback.message.caption
    target_user = "Noma'lum"
    if "👤 Oluvchi:" in caption:
        target_user = caption.split("👤 Oluvchi:")[1].split("\n")[0].strip()

    if "Stars" in product:
        try:
            stars_to_add = int(product.split(" ")[0])
            conn = sqlite3.connect("bot_main_data.db")
            cursor = conn.cursor()
            
            # Oluvchi bazada bormi? (Username yoki ID bo'yicha)
            cursor.execute("SELECT id FROM users WHERE username=? OR id=?", (target_user, target_user.replace("@", "")))
            target_data = cursor.fetchone()
            
            if target_data:
                # Oluvchi bazada bo'lsa, uning hisobiga qo'shamiz
                cursor.execute("UPDATE users SET total_stars = total_stars + ? WHERE id=?", (stars_to_add, target_data[0]))
            else:
                # Oluvchi bazada bo'lmasa, uni yangi foydalanuvchi sifatida qo'shib, keyin yulduz beramiz
                cursor.execute("INSERT INTO users (name, username, total_stars) VALUES (?, ?, ?)", 
                               ("Oluvchi", target_user, stars_to_add))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Stars qo'shishda xato: {e}")

    await bot.send_message(user_id, f"✅ Buyurtmangiz tasdiqlandi! Stars {target_user} profiliga yuborildi.")
    await callback.message.edit_caption(caption=f"{caption}\n\n✅ **TASDIQLANDI**")

@dp.message(F.text == "👨‍💻 Admin bilan bogʻlanish")
async def contact_admin(message: types.Message):
    await message.answer(f"Admin bilan bog'lanish: @{ADMIN_USERNAME}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())