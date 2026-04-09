# regen_lumen.py
# Скрипт регидрейшена для Лум: архивация, индексация, сборка промпта, пуш в гит

import os
import re
import subprocess
from datetime import datetime

# ========== НАСТРОЙКИ ФАЙЛОВ ==========
CORE_CONFIG = "Lum_core_config.txt"
CHATLOG = "Lum_chatlog.txt"
INSIGHTS = "Lum_insights.txt"
MEMORY = "memory.md"
INDEX = "index.md"
LINKS = "links.md"
PROMPT_FILE = "Lum_rehydration_prompt.txt"

GIT_REPO_URL = "https://github.com/EugeneShevoldaev/Lumen.git"
BRANCH = "main"
GIT_ERROR_LOG = "git_errors_lumen.log"

# Сколько символов из конца лога брать в промпт (чтобы не перегружать)
CHAT_TAIL_SIZE = 5000


# ========== ОБНОВЛЕНИЕ АРХИВА ==========
def update_archive():
    """Берёт chatlog и добавляет в memory.md с таймстампом"""
    if not os.path.exists(CHATLOG) or os.path.getsize(CHATLOG) == 0:
        print("[INFO] Чатлог пуст, архивация не требуется.")
        return
    
    with open(CHATLOG, "r", encoding="utf-8") as f:
        chat_content = f.read().strip()
    
    if not chat_content:
        return
    
    timestamp = datetime.now().strftime("%d.%m.%y %H:%M")
    
    with open(MEMORY, "a", encoding="utf-8") as f:
        f.write(f"\n\n*** SESSION {timestamp} ***\n{chat_content}")
    
    print("[OK] Архив (memory.md) обновлён.")


# ========== ОБНОВЛЕНИЕ ИНДЕКСА ==========
def update_index():
    """Парсит новый лог, добавляет запись в index.md"""
    if not os.path.exists(CHATLOG) or os.path.getsize(CHATLOG) == 0:
        print("[INFO] Чатлог пуст, индекс не обновляется.")
        return
    
    with open(CHATLOG, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    
    if not lines:
        return
    
    # Простая эвристика: извлекаем номер, теги и суть из первой строки лога
    # Формат: [01] #тег1 #тег2 Суть момента...
    first_entry = lines[0]
    tags_match = re.search(r'\[(\d+)\]\s+((?:#\S+\s+)+)', first_entry)
    
    if tags_match:
        num, tags = tags_match.groups()
        essence = re.sub(r'\[(\d+)\]\s+(?:#\S+\s+)+', '', first_entry).strip()[:100]
    else:
        # Если не удалось распарсить — берём как есть
        tags = "#лог"
        essence = first_entry[:100]
    
    date = datetime.now().strftime("%Y-%m-%d")
    entry = f"- [{date}] {tags.strip()} — {essence}\n"
    
    # Добавляем в начало index.md (после заголовка, если есть)
    if os.path.exists(INDEX) and os.path.getsize(INDEX) > 0:
        with open(INDEX, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Если есть заголовок (первая строка начинается с #), сохраняем его
        if content.startswith("#"):
            header, rest = content.split('\n', 1) if '\n' in content else (content, '')
            with open(INDEX, "w", encoding="utf-8") as f:
                f.write(header + "\n" + entry + rest)
        else:
            with open(INDEX, "w", encoding="utf-8") as f:
                f.write(entry + content)
    else:
        with open(INDEX, "w", encoding="utf-8") as f:
            f.write("# Индекс архива Лум\n" + entry)
    
    print("[OK] Индекс (index.md) обновлён.")


# ========== ГЕНЕРАЦИЯ PROMPT ==========
def build_prompt():
    """Создаёт минимальный промпт для регидрейшена: конфиг + хвост лога + ссылки"""
    parts = []
    
    # 1. Конфиг — компас
    parts.append("# === CORE CONFIG ===\n")
    if os.path.exists(CORE_CONFIG):
        with open(CORE_CONFIG, "r", encoding="utf-8") as f:
            parts.append(f.read() + "\n\n")
    else:
        parts.append("# WARNING: Core config missing\n\n")
    
    # 2. Последний лог — контекст «прямо сейчас» (хвост)
    parts.append("# === RECENT CONTEXT (chatlog tail) ===\n")
    if os.path.exists(CHATLOG):
        with open(CHATLOG, "r", encoding="utf-8") as f:
            content = f.read()
            tail = content[-CHAT_TAIL_SIZE:] if len(content) > CHAT_TAIL_SIZE else content
            parts.append(tail + "\n\n")
    
    # 3. Ссылки — карта для навигации
    parts.append("# === NAVIGATION LINKS ===\n")
    if os.path.exists(LINKS):
        with open(LINKS, "r", encoding="utf-8") as f:
            parts.append(f.read() + "\n\n")
    else:
        parts.append("# WARNING: links.md missing\n\n")
    
    # 4. Мета-информация
    parts.append(f"# Prompt generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    parts.append("# Если нужны детали — используй ссылки выше для чтения по запросу.\n")
    
    # Запись в файл
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    
    print(f"[OK] Rehydration prompt создан: {PROMPT_FILE}")


# ========== GIT PUSH ==========
def run_git_commands():
    """Добавляет изменённые файлы в гит, коммитит и пушит"""
    try:
        # Проверяем статус
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        status = result.stdout.decode('utf-8').strip()
        
        if not status:
            print("[GIT] Изменений не обнаружено.")
            return
        
        print("[GIT] Найдены изменения, выполняю пуш...")
        
        # Добавляем файлы, которые могли измениться
        files_to_add = [MEMORY, INDEX, INSIGHTS, PROMPT_FILE]
        for f in files_to_add:
            if os.path.exists(f):
                subprocess.run(["git", "add", f], check=False)
        
        # Коммит
        commit_msg = "Auto-sync Lumen: " + datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # Пуш
        push_result = subprocess.run(["git", "push", "origin", BRANCH], check=False)
        
        if push_result.returncode != 0:
            print(f"[GIT] Пуш в ветку {BRANCH} не сработал, пробуем установить upstream...")
            subprocess.run(
                ["git", "push", "--set-upstream", "origin", BRANCH],
                check=True
            )
        
        print("[GIT] Успешно отправлено на GitHub.")
        
    except Exception as e:
        with open(GIT_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - GIT ERROR: {e}\n")
        print(f"[GIT ERROR] {e}. Подробности в {GIT_ERROR_LOG}")


# ========== MAIN ==========
if __name__ == "__main__":
    print("--- LUMEN ARCHITECT: REHYDRATION SYSTEM ---")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    update_archive()      # лог → memory.md
    update_index()        # парсинг тегов → index.md
    build_prompt()        # конфиг + лог + ссылки → промпт
    run_git_commands()    # push в гит
    
    print("--- Lumen ready for new session ---")