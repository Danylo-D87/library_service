# payments/tasks.py або notifications/tasks.py

from celery import shared_task
import requests
from django.conf import settings


@shared_task
def send_telegram_payment_notification(data: dict):
    try:
        message = (
            f"💸 *Payment success*\n"
            f"User: `{data['user']}`\n"
            f"Type: `{data['type']}`\n"
            f"Sum: `${data['amount']}`\n"
            f"Borrow ID: `{data['borrowing_id']}`\n"
            f"Book: *{data['book']}*"
        )
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[Telegram Celery task error]: {e}")
