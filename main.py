import logging
import asyncio
import os
import requests
import time
from threading import Thread
from background import keep_alive
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from PIL import Image

user_choice = {}  # Хранит текущий выбор пользователя (size или opacity)
user_opacity = {}  # Словарь для хранения значений пользователей
user_size = {}  # Словарь для хранения значений пользователей

# Словарь переводов
translations = {
    "start": {
        "ru": "Привет! 😊\n\nДобро пожаловать! Этот бот поможет вам добавить водяной знак на изображения. 🔥\n\n📌 Что нужно сделать?\n📎 Загрузите файл с изображением или логотипом, который хотите использовать в качестве водяного знака.\n\n⚠ Важно! Отправляйте изображение только файлом, а не как сжатое фото. Убедитесь, что оно имеет подходящий размер и (если необходимо) прозрачный фон.\n\nПосле загрузки вы сможете настроить его положение, размер и прозрачность!\n\nПожалуйста, загрузите водяной знак. 😊 🚀",
        "en": "Hello! Send me a logo (JPG or PNG).",
        "uk": "Привіт! Надішли мені логотип (JPG або PNG)."
    },
    "menu": {
        "ru": "Выберите действие:",
        "en": "Choose an action:",
        "uk": "Виберіть дію:"
    },
    "choose_language": {
        "ru": "Выберите язык:",
        "en": "Choose a language:",
        "uk": "Виберіть мову:"
    },
    "language_selected": {
        "ru": "✅ Вы выбрали Русский.",
        "en": "✅ You have selected English.",
        "uk": "✅ Ви обрали Українську."
    },
    "logo_deleted": {
        "ru": "✅ Ваш водяной знак удалён.\n\nПожалуйста, загрузите новый водяной знак. 😊 🚀",
        "en": "✅ Your logo has been deleted. Send a new logo.",
        "uk": "✅ Ваш логотип видалено. Надішліть новий логотип."
    },
    "unsupported_format": {
        "ru": "⚠ Поддерживаются только форматы JPG и PNG!",
        "en": "⚠ Only JPG and PNG formats are supported!",
        "uk": "⚠ Підтримуються лише формати JPG і PNG!"
    },
    "logo_saved": {
        "ru": "✅ Логотип ({}) сохранён! Теперь отправьте фото для водяного знака.",
        "en": "✅ Logo ({}) saved! Now send a photo for the watermark.",
        "uk": "✅ Логотип ({}) збережено! Тепер надішліть фото для водяного знака."
    },
    "logo_saved_jpg": {
        "ru": "✅ Логотип (JPG) сохранён! Теперь отправьте фото для водяного знака.",
        "en": "✅ Logo (JPG) saved! Now send a photo for the watermark.",
        "uk": "✅ Логотип (JPG) збережено! Тепер надішліть фото для водяного знака."
    },
    "png_warning": {
        "ru": "⚠ Если у вас PNG с прозрачностью, загружайте его как ФАЙЛ (📎), иначе фон станет белым!",
        "en": "⚠ If you have a PNG with transparency, upload it as a FILE (📎), otherwise the background will turn white!",
        "uk": "⚠ Якщо у вас PNG з прозорістю, завантажуйте його як ФАЙЛ (📎), інакше фон стане білим!"
    },
    "upload_logo_first": {
        "ru": "⚠ Сначала загрузите логотип (JPG или PNG)!",
        "en": "⚠ First, upload a logo (JPG or PNG)!",
        "uk": "⚠ Спочатку завантажте логотип (JPG або PNG)!"
    },
    "unsupported_image_format": {
        "ru": "⚠ Поддерживаются только JPG и PNG!",
        "en": "⚠ Only JPG and PNG formats are supported!",
        "uk": "⚠ Підтримуються лише формати JPG і PNG!"
    },
    "watermark_added": {
        "ru": "✅ Готово! Водяной знак добавлен.",
        "en": "✅ Done! Watermark added.",
        "uk": "✅ Готово! Водяний знак додано."
    },
    "unsupported_format": {
        "ru": "❌ Формат файла не поддерживается. Пожалуйста, загрузите файл в формате JPG или PNG.",
    },
    "logo_saved": {
        "ru": "✅ Ваш водяной знак сохранён в формате {}.\n\nТеперь вы можете:\n🔹 Удалить водяной знак – если он больше не нужен.\n🔹 Выбрать место водяного знака – укажите, куда его разместить.\n🔹 Настроить прозрачность – сделайте водяной знак более заметным или незаметным.\n🔹 Изменить размер водяного знака – увеличьте или уменьшите его под нужный формат.\n\nТеперь загрузите изображение, на которое нужно наложить водяной знак 🚀",
    },
    "photo_not_allowed": {
        "ru": "❌ Загрузка водяного знака через отправку изображения запрещена!",
    },
    "please_upload_file": {
        "ru": "📄 Пожалуйста, загрузите изображение водяного знака в виде файла.",
    },

}

# Токен бота
API_TOKEN = '8051188195:AAF69e5tHSU80MR2YBTD0eaNM7Eq5wQ-xf0'

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
processing_lock = asyncio.Lock()
# Папки для хранения изображений
IMAGE_DIR = "images"
WATERMARK_DIR = "watermarks"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(WATERMARK_DIR, exist_ok=True)

# Глобальный словарь для хранения выбранной позиции водяного знака для каждого пользователя
# По умолчанию: "справа" (нижний правый угол)
watermark_positions = {}
# Словарь для хранения выбранного языка пользователей
user_languages = {}

# Основная клавиатура
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗑 Удалить водяной знак"), KeyboardButton(text="🔍 Выбрать место водяного знака")],
        [KeyboardButton(text="⚙️ Настройка прозрачности"), KeyboardButton(text="📏 Изменить размер водяного знака")],
        #[KeyboardButton(text="🌍 Выбрать язык")]
    ],
    resize_keyboard=True
)
    # Клавиатура для выбора размера водяного знака
size_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="10%"), KeyboardButton(text="20%"), KeyboardButton(text="30%")],
        [KeyboardButton(text="40%"), KeyboardButton(text="50%"), KeyboardButton(text="60%")],
        [KeyboardButton(text="70%"), KeyboardButton(text="80%"), KeyboardButton(text="90%")],
        [KeyboardButton(text="100%")],
        [KeyboardButton(text="⬅️ Назад")]  # Кнопка назад к главному меню
    ],
    resize_keyboard=True
)






# Клавиатура для выбора позиции водяного знака
position_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="слева вверху"), KeyboardButton(text="вверху"), KeyboardButton(text="справа вверху")],
        [KeyboardButton(text="слева"), KeyboardButton(text="по центру"), KeyboardButton(text="справа"),],
        [KeyboardButton(text="слева внизу"), KeyboardButton(text="внизу"), KeyboardButton(text="спарава внизу")],
        [KeyboardButton(text="⬅️ Назад")]  # Кнопка назад к главному меню
    ],
    resize_keyboard=True
)

opacity_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="10%"), KeyboardButton(text="20%"), KeyboardButton(text="30%")],
        [KeyboardButton(text="40%"), KeyboardButton(text="50%"), KeyboardButton(text="60%")],
        [KeyboardButton(text="70%"), KeyboardButton(text="80%"), KeyboardButton(text="90%")],
        [KeyboardButton(text="100%")],
        [KeyboardButton(text="⬅️ Назад")]  # Кнопка назад к главному меню
    ],
    resize_keyboard=True
)
@dp.message(lambda message: message.text == "📏 Изменить размер водяного знака")
async def choose_size(message: types.Message):
    user_id = message.from_user.id
    user_choice[user_id] = "size"  # Запоминаем, что пользователь меняет размер
    await message.answer("Выберите размер водяного знака:", reply_markup=size_keyboard)


@dp.message(lambda message: message.text == "⚙️ Настройка прозрачности")
async def choose_opacity(message: types.Message):
    user_id = message.from_user.id
    user_choice[user_id] = "opacity"  # Запоминаем, что пользователь меняет прозрачность
    await message.answer("Выберите уровень прозрачности:", reply_markup=opacity_keyboard)


@dp.message(lambda message: message.text and message.text.rstrip('%').isdigit())
async def handle_percentage(message: types.Message):
    user_id = message.from_user.id
    percent = int(message.text.rstrip('%'))

    if 0 <= percent <= 100:
        if user_id in user_choice:
            if user_choice[user_id] == "size":
                user_size[user_id] = percent / 100.0
                await message.answer(f"✅ Размер установлен на {percent}%\n\nЗагрузите изображение, на которое нужно наложить водяной знак 🚀", reply_markup=menu_keyboard)
            elif user_choice[user_id] == "opacity":
                user_opacity[user_id] = percent / 100.0
                await message.answer(f"✅ Прозрачность установлена на {percent}%\n\nЗагрузите изображение, на которое нужно наложить водяной знак 🚀", reply_markup=menu_keyboard)

            del user_choice[user_id]  # Сбрасываем выбор после установки значения
        else:
            await message.answer("Ошибка: сначала выберите параметр (размер или прозрачность).")
    else:
        await message.answer("Пожалуйста, выберите значение от 0% до 100%.")






# Глобальная переменная для хранения текущей прозрачности




@dp.message(lambda message: message.text == "⬅️ Назад")
async def back_to_menu(message: types.Message):
    await message.answer("✅ Главное меню", reply_markup=menu_keyboard)  # Точка, чтобы не было пустого сообщения


# Клавиатура для выбора языка
language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇬🇧 English")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇺🇦 Українська")]
    ],
    resize_keyboard=True
)

@dp.message(lambda message: message.text in ["🇬🇧 English", "🇷🇺 Русский", "🇺🇦 Українська"])
async def set_language(message: Message):
    user_id = message.from_user.id

    # Определяем язык по кнопке
    if message.text == "🇷🇺 Русский":
        user_languages[user_id] = "ru"
    elif message.text == "🇬🇧 English":
        user_languages[user_id] = "en"
    elif message.text == "🇺🇦 Українська":
        user_languages[user_id] = "uk"

    # Отправляем сообщение на выбранном языке
    lang = user_languages[user_id]
    await message.answer(translations["language_selected"][lang], reply_markup=menu_keyboard)


@dp.message(lambda message: message.text == "🌍 Выбрать язык")
async def choose_language(message: Message):
    await message.answer("Выберите язык:", reply_markup=language_keyboard)

# Команда /start
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")  # По умолчанию русский
    await message.answer(translations["start"][lang], reply_markup=menu_keyboard)

# Команда /menu
@dp.message(Command("menu"))
async def menu_cmd(message: Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")  # По умолчанию русский
    await message.answer(translations["menu"][lang], reply_markup=menu_keyboard)

# Удаление логотипа
@dp.message(lambda message: message.text == "🗑 Удалить водяной знак")
async def delete_logo(message: Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")  # По умолчанию русский

    watermark_path_jpg = os.path.join(WATERMARK_DIR, f"{user_id}.jpg")
    watermark_path_png = os.path.join(WATERMARK_DIR, f"{user_id}.png")

    if os.path.exists(watermark_path_jpg):
        os.remove(watermark_path_jpg)
    if os.path.exists(watermark_path_png):
        os.remove(watermark_path_png)

    await message.answer(translations["logo_deleted"][lang], reply_markup=menu_keyboard)


# Выбор места водяного знака
@dp.message(lambda message: message.text == "🔍 Выбрать место водяного знака")
async def choose_position(message: Message):
    await message.answer("Выберите место для водяного знака:", reply_markup=position_keyboard)

# Обработчик выбора позиции водяного знака
@dp.message(lambda message: message.text in ["слева внизу", "спарава внизу", "слева вверху", "справа вверху", "слева", "справа", "вверху", "внизу", "по центру"])
async def set_position(message: Message):
    user_id = message.from_user.id
    watermark_positions[user_id] = message.text
    await message.answer(f"✅ Позиция водяного знака установлена: {message.text}.\n\nЗагрузите изображение, на которое нужно наложить водяной знак 🚀", reply_markup=menu_keyboard)

































# Директория для логотипов
WATERMARK_DIR = "watermarks"
os.makedirs(WATERMARK_DIR, exist_ok=True)

# Функция для проверки наличия логотипа
def has_logo(user_id):
    for ext in ["jpg", "jpeg", "png"]:
        if os.path.exists(os.path.join(WATERMARK_DIR, f"{user_id}.{ext}")):
            return True
    return False

# Обработчик документов для логотипов
@dp.message(lambda message: message.document and not has_logo(message.from_user.id))
async def handle_document(message: Message):
    user_id = message.from_user.id
    document = message.document

    if not document:
        await message.answer("❌ Ошибка: файл не найден. Попробуйте снова.")
        return

    lang = user_languages.get(user_id, "ru")
    file_name = document.file_name or "unknown"
    file_ext = file_name.split('.')[-1].lower()

    if file_ext not in ["jpg", "png"]:
        await message.answer(translations["unsupported_format"][lang])
        return

    file = await bot.get_file(document.file_id)
    if not file or not file.file_path:
        await message.answer("❌ Ошибка: не удалось получить файл.")
        return

    watermark_path = os.path.join(WATERMARK_DIR, f"{user_id}.{file_ext}")
    await bot.download_file(file.file_path, watermark_path)
    await message.answer(translations["logo_saved"][lang].format(file_ext.upper()))

# Обработчик фото (только для предупреждения при загрузке логотипов)
@dp.message(lambda message: message.photo and not has_logo(message.from_user.id))
async def handle_photo_logo(message: Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")

    await message.answer(translations["photo_not_allowed"][lang])
    await message.answer(translations["please_upload_file"][lang])


@dp.message(lambda message: message.photo or (message.document and message.document.mime_type.startswith("image/")))
async def handle_image(message: Message):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")  # Получаем язык пользователя

    async with processing_lock:  # Блокируем обработку
        # Проверяем, есть ли логотип
        watermark_path = os.path.join(WATERMARK_DIR, f"{user_id}.png")
        if not os.path.exists(watermark_path):
            watermark_path = os.path.join(WATERMARK_DIR, f"{user_id}.jpg")

        if not os.path.exists(watermark_path):
            await message.answer(translations["upload_logo_first"][lang])
            return

        # Определяем имя файла и путь
        if message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            image_path = os.path.join(IMAGE_DIR, f"{user_id}.jpg")
        else:
            document = message.document
            file_ext = document.file_name.split('.')[-1].lower()
            if file_ext not in ["jpg", "jpeg", "png"]:
                await message.answer(translations["unsupported_image_format"][lang])
                return
            file = await bot.get_file(document.file_id)
            image_path = os.path.join(IMAGE_DIR, f"{user_id}.{file_ext}")

        # Загружаем фото
        await bot.download_file(file.file_path, image_path)

        # Обрабатываем изображение
        result_path = add_watermark(image_path, watermark_path, watermark_positions.get(user_id, "по центру"), user_id)
        photo_file = FSInputFile(result_path)
        await message.answer_document(photo_file, caption=translations["watermark_added"][lang])


# Функция наложения прозрачного водяного знака с учетом выбранной позиции
def add_watermark(image_path, watermark_path, position_choice, user_id):
    opacity_value = user_opacity.get(user_id, 0.5)  # Убираем str()  # Берём значение, 0.5 по умолчанию
    size_value = user_size.get(user_id, 0.2) 

    base_image = Image.open(image_path).convert("RGBA")
    watermark = Image.open(watermark_path).convert("RGBA")

    # Изменяем размер водяного знака (20% от ширины изображения)
    base_width, base_height = base_image.size
    wm_width = int(base_width * size_value)
    wm_height = int(watermark.height * (wm_width / watermark.width))
    watermark = watermark.resize((wm_width, wm_height), Image.LANCZOS)

    # Применяем индивидуальную прозрачность
    alpha = watermark.split()[3]  # Берём альфа-канал
    alpha = alpha.point(lambda p: p * opacity_value)  # Применяем значение пользователя
    watermark.putalpha(alpha)

    # Определяем позицию водяного знака
    positions = {
        "слева": (10, (base_height - wm_height) // 2),
        "справа": (base_width - wm_width - 10, (base_height - wm_height) // 2),
        "вверху": ((base_width - wm_width) // 2, 10),
        "внизу": ((base_width - wm_width) // 2, base_height - wm_height - 10),
        "по центру": ((base_width - wm_width) // 2, (base_height - wm_height) // 2),
        "слева вверху": (10, 10),
        "справа вверху": (base_width - wm_width - 10, 10),
        "слева внизу": (10, base_height - wm_height - 10),
        "справа внизу": (base_width - wm_width - 10, base_height - wm_height - 10),
    }
    position = positions.get(position_choice, (base_width - wm_width - 10, base_height - wm_height - 10))

    # Накладываем водяной знак
    transparent = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    transparent.paste(base_image, (0, 0))
    transparent.paste(watermark, position, mask=watermark)

    # Сохраняем в PNG (чтобы не терять прозрачность)
    result_path = image_path.replace(".jpg", "_watermark_master_bot.jpg").replace(".png", "_watermark_master_bot.png")
    transparent.save(result_path, "PNG")

    return result_path


def ping_self():
    while True:
        try:
            response = requests.get("https://395f39e6-f686-4c61-baf4-e970c347044d-00-mpe9dazqkzef.worf.replit.dev:8080/")  # Замени на свой URL
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Пинг успешен! Код: {response.status_code}")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка пинга: {e}")
        time.sleep(240)  # Пинговать каждые 10 минут


# Запускаем Flask для удержания активности
keep_alive()

# Запускаем пинг в отдельном потоке
t2 = Thread(target=ping_self)
t2.start()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
