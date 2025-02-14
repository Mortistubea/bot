from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup


tekshirish_tugma = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Obunani tekshirish", 
                        callback_data='check_subscribe')
        ]
    ]
)