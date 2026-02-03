import os
import hashlib
import subprocess
from datetime import date

import boto3
import httpx
from celery import shared_task

from src.config import settings


def get_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f:
            if line.startswith(b"--"):
                continue
            h.update(line)
    return h.hexdigest()

def _upload_backup_to_s3(filepath: str, object_key: str) -> str | None:
    if not settings.S3_ACCESS_KEY:
        return None
    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            region_name=settings.S3_REGION or None,
        )
        client.upload_file(
            filepath,
            settings.S3_BUCKET_NAME,
            object_key,
            ExtraArgs={"ContentType": "application/sql"},
        )
        url = f"{settings.S3_PUBLIC_URL.rstrip('/')}/{object_key}"
        print(f"Бекап загружен в S3: {url}")
        return url
    except Exception as e:
        print(f"Ошибка загрузки в S3: {e}")
        return None


@shared_task
def send_db_backup_task():
    filename = f"/fastapi_app/tmp/backup_{settings.DB_NAME}.sql"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    hash_path = f"{filename}.sha256"
    old_hash = None

    if os.path.exists(hash_path):
        with open(hash_path, "r") as f:
            old_hash = f.read().strip()
    else:
        old_hash = get_file_hash(filename) if os.path.exists(filename) else None

    print(f"📦 Создание бекапа базы данных {settings.DB_NAME}...")

    try:
        subprocess.run(
            ["pg_dump", "-h", settings.DB_HOST, "-U", settings.DB_USER, "-d", settings.DB_NAME, "--exclude-table-data=user_logs", "-f", filename],
            check=True,
            env={**os.environ, "PGPASSWORD": settings.DB_PASS},
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при создании дампа: {e}")
        return

    current_hash = get_file_hash(filename)

    if current_hash == old_hash:
        print("⏩ Изменений в БД нет — бэкап не отправляется")
        return

    with open(hash_path, "w") as f:
        f.write(current_hash)

    today = date.today().isoformat()
    s3_key = f"backups/parfum_db/{today}/{settings.DB_NAME}_{today}.sql"
    _upload_backup_to_s3(filename, s3_key)

    print("✅ Бекап изменён. Отправка в Telegram...")
    try:
        with open(filename, "rb") as f:
            response = httpx.post(
                url=f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendDocument",
                data={"chat_id": settings.TG_CHAT_ID, "caption": f"Бэкап за {date.today()}"},
                files={"document": f}
            )
        if response.status_code == 200:
            print("✅ Бекап отправлен в Telegram")
        else:
            print(f"❌ Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")
