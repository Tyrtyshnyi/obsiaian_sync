import os
import time
import requests
import dotenv
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

env_path = Path(".env")
if env_path.exists():
    dotenv.load_dotenv(dotenv_path=env_path)

#функция для транзакций .env
def get_or_ask(var_name: str, prompt: str, default: str = None):
    value = os.getenv(var_name)
    if value:
        print(f'{var_name} взят из .env: "{value}"')
    else:
        user_input = input(f"{prompt} [{default if default else ''}]: ").strip()
        value = user_input if user_input else default
        dotenv.set_key(dotenv_path=env_path, key_to_set=var_name, value_to_set=value)
        print(f'{var_name} сохранён в .env: "{value}"')
    return value


YandexToken = get_or_ask("YANDEX_TOKEN", "Введите Яндекс токен")
YandexAPI   = get_or_ask("YANDEX_API", "Введите API Яндекса", default="https://cloud-api.yandex.net/v1/disk/resources")
VAULT_PATH  = Path(get_or_ask("VAULT_PATH", "Путь к Obsidian Vault", default=str(Path.cwd())))
REMOTE_DIR  = get_or_ask("REMOTE_DIR", "Папка на Яндекс.Диске", default="disk:/Obsidian")
HEADERS = {"Authorization": f"OAuth {YandexToken}"}

print(f"\nVAULT_PATH: {VAULT_PATH}")
print(f"REMOTE_DIR: {REMOTE_DIR}\n")

#  функции работы с ядиском (в будущем можно вынести в класс)
def upload_file(local_path: Path):
    remote_path = f"{REMOTE_DIR}/{local_path.relative_to(VAULT_PATH)}"
    url = f"{YandexAPI}/upload?path={remote_path}&overwrite=true"
    try:
        r = requests.get(url, headers=HEADERS)
        href = r.json().get("href")
        if href:
            with open(local_path, "rb") as f:
                requests.put(href, data=f)
            print(f'⬆️ Залил: "{remote_path}"')
    except Exception as e:
        print(f"Ошибка при загрузке {local_path}: {e}")

def delete_file(local_path: Path):
    remote_path = f"{REMOTE_DIR}/{local_path.relative_to(VAULT_PATH)}"
    url = f"{YandexAPI}?path={remote_path}"
    try:
        requests.delete(url, headers=HEADERS)
        print(f'🗑️ Удалил: "{remote_path}"')
    except Exception as e:
        print(f"Ошибка при удалении {local_path}: {e}")

# --- класс наблюдателя ---
class VaultHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            upload_file(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            upload_file(Path(event.src_path))

    def on_deleted(self, event):
        if not event.is_directory:
            delete_file(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            delete_file(Path(event.src_path))
            upload_file(Path(event.dest_path))

# --- запуск наблюдателя ---
observer = Observer()
event_handler = VaultHandler()
observer.schedule(event_handler, str(VAULT_PATH), recursive=True)
observer.start()

try:
    print(f"👀 Слежу за {VAULT_PATH} ...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
