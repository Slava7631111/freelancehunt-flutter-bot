# import json
# import logging
# import os
# import re
# import time
# from pathlib import Path
# from typing import Any

# import requests
# from dotenv import load_dotenv

# load_dotenv()

# FREELANCEHUNT_API = "https://api.freelancehunt.com/v2"
# TELEGRAM_API = "https://api.telegram.org"
# STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))

# FREELANCEHUNT_TOKEN = os.getenv("FREELANCEHUNT_TOKEN", "").strip()
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
# AUTO_BID = os.getenv("AUTO_BID", "true").lower() in {"1", "true", "yes", "on"}
# DRY_RUN = os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "on"}

# DEFAULT_BID_AMOUNT = int(os.getenv("DEFAULT_BID_AMOUNT", "5000"))
# DEFAULT_BID_CURRENCY = os.getenv("DEFAULT_BID_CURRENCY", "UAH").upper()
# DEFAULT_DAYS = int(os.getenv("DEFAULT_DAYS", "7"))
# SAFE_TYPE = os.getenv("SAFE_TYPE", "employer").strip() or "employer"

# KEYWORDS = [
#     x.strip().lower()
#     for x in os.getenv(
#         "KEYWORDS",
#         "flutter,dart,мобильное приложение,мобільний застосунок,мобільний додаток,ios android,android ios",
#     ).split(",")
#     if x.strip()
# ]
# STOP_WORDS = [
#     x.strip().lower()
#     for x in os.getenv(
#         "STOP_WORDS",
#         "react native,kotlin only,swift only,unity,game,игра,гра",
#     ).split(",")
#     if x.strip()
# ]

# BID_TEMPLATE = os.getenv(
#     "BID_TEMPLATE",
#     (
#         "Здравствуйте! Я Flutter-разработчик и могу выполнить ваш проект «{title}». "
#         "Сделаю приложение на Flutter под Android/iOS, подключу API/Firebase при необходимости, "
#         "реализую аккуратный UI и подготовлю рабочую сборку. "
#         "Готов быстро обсудить детали и начать работу."
#     ),
# )

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s",
# )
# log = logging.getLogger("freelancehunt-bot")

# session = requests.Session()


# def require_settings() -> None:
#     missing = []

#     if not FREELANCEHUNT_TOKEN:
#         missing.append("FREELANCEHUNT_TOKEN")

#     if not TELEGRAM_BOT_TOKEN:
#         missing.append("TELEGRAM_BOT_TOKEN")

#     if not TELEGRAM_CHAT_ID:
#         missing.append("TELEGRAM_CHAT_ID")

#     if missing:
#         raise RuntimeError("Заполни в .env: " + ", ".join(missing))


# def fh_headers() -> dict[str, str]:
#     return {
#         "Authorization": f"Bearer {FREELANCEHUNT_TOKEN}",
#         "Accept-Language": "ru",
#         "Content-Type": "application/json",
#     }


# def load_state() -> dict[str, Any]:
#     if not STATE_FILE.exists():
#         return {"seen": [], "bid": []}
#     try:
#         data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
#         data.setdefault("seen", [])
#         data.setdefault("bid", [])
#         return data
#     except Exception:
#         log.exception("Не удалось прочитать state.json, создаю новый")
#         return {"seen": [], "bid": []}


# def save_state(state: dict[str, Any]) -> None:
#     # Не даём файлу расти бесконечно.
#     state["seen"] = list(dict.fromkeys(state.get("seen", [])))[-5000:]
#     state["bid"] = list(dict.fromkeys(state.get("bid", [])))[-5000:]
#     STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# def strip_html(text: str) -> str:
#     text = re.sub(r"<[^>]+>", " ", text or "")
#     text = re.sub(r"\s+", " ", text)
#     return text.strip()


# def project_text(project: dict[str, Any]) -> str:
#     attrs = project.get("attributes", {}) or {}
#     title = str(attrs.get("name") or "")
#     description = strip_html(str(attrs.get("description_html") or attrs.get("description") or ""))
#     tags = " ".join(str(x) for x in (attrs.get("tags") or []))

#     skills = attrs.get("skills") or []
#     skill_texts = []
#     for skill in skills:
#         if isinstance(skill, dict):
#             skill_texts.append(str(skill.get("name") or skill.get("id") or ""))
#         else:
#             skill_texts.append(str(skill))

#     return " ".join([title, description, tags, " ".join(skill_texts)]).lower()


# def is_flutter_project(project: dict[str, Any]) -> bool:
#     text = project_text(project)
#     if any(stop in text for stop in STOP_WORDS):
#         return False
#     return any(keyword in text for keyword in KEYWORDS)


# def get_open_projects(max_pages: int = 3) -> list[dict[str, Any]]:
#     projects: list[dict[str, Any]] = []
#     for page in range(1, max_pages + 1):
#         url = f"{FREELANCEHUNT_API}/projects"
#         r = session.get(
#             url,
#             headers=fh_headers(),
#             params={"page[number]": page},
#             timeout=25,
#         )
#         if r.status_code == 429:
#             retry = int(r.headers.get("Retry-After", "30"))
#             log.warning("Freelancehunt rate limit. Пауза %s сек.", retry)
#             time.sleep(retry)
#             continue
#         r.raise_for_status()
#         payload = r.json()
#         batch = payload.get("data", []) or []
#         projects.extend(batch)
#         links = payload.get("links", {}) or {}
#         if not links.get("next"):
#             break
#     return projects


# def project_url(project_id: str | int) -> str:
#     return f"https://freelancehunt.com/project/{project_id}.html"


# def get_budget(project: dict[str, Any]) -> tuple[int, str]:
#     attrs = project.get("attributes", {}) or {}
#     budget = attrs.get("budget") or {}
#     if isinstance(budget, dict):
#         amount = budget.get("amount")
#         currency = budget.get("currency")
#         try:
#             if amount and int(float(amount)) > 0:
#                 return int(float(amount)), str(currency or DEFAULT_BID_CURRENCY).upper()
#         except (TypeError, ValueError):
#             pass
#     return DEFAULT_BID_AMOUNT, DEFAULT_BID_CURRENCY


# def build_bid_comment(project: dict[str, Any]) -> str:
#     attrs = project.get("attributes", {}) or {}
#     title = str(attrs.get("name") or "вашему проекту").strip()
#     comment = BID_TEMPLATE.format(title=title)
#     # В отклике не должно быть HTML; делаем компактнее.
#     return strip_html(comment)[:1500]


# def send_telegram(text: str) -> None:
#     url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
#     r = session.post(
#         url,
#         json={
#             "chat_id": TELEGRAM_CHAT_ID,
#             "text": text,
#             "disable_web_page_preview": True,
#         },
#         timeout=20,
#     )
#     r.raise_for_status()


# def add_bid(project: dict[str, Any]) -> tuple[bool, str]:
#     project_id = project.get("id")
#     amount, currency = get_budget(project)
#     comment = build_bid_comment(project)

#     body = {
#         "days": DEFAULT_DAYS,
#         "safe_type": SAFE_TYPE,
#         "budget": {"amount": amount, "currency": currency},
#         "comment": comment,
#         "is_hidden": False,
#     }

#     if DRY_RUN:
#         return True, f"DRY_RUN: ставка {amount} {currency}, {DEFAULT_DAYS} дн.; {comment}"

#     r = session.post(
#         f"{FREELANCEHUNT_API}/projects/{project_id}/bids",
#         headers=fh_headers(),
#         json=body,
#         timeout=25,
#     )

#     if r.status_code in (200, 201):
#         return True, f"Отклик отправлен: {amount} {currency}, {DEFAULT_DAYS} дн."

#     # Возвращаем короткое описание ошибки, не токены/секреты.
#     try:
#         error = r.json()
#     except Exception:
#         error = r.text[:500]
#     return False, f"Freelancehunt ответил {r.status_code}: {error}"


# def format_project_message(project: dict[str, Any]) -> str:
#     pid = project.get("id")
#     attrs = project.get("attributes", {}) or {}
#     title = str(attrs.get("name") or "Без названия")
#     description = strip_html(str(attrs.get("description_html") or attrs.get("description") or ""))
#     amount, currency = get_budget(project)
#     excerpt = description[:500] + ("…" if len(description) > 500 else "")

#     return (
#         "🟦 Новый Flutter-заказ на Freelancehunt\n\n"
#         f"{title}\n"
#         f"💰 Бюджет для ставки: {amount} {currency}\n"
#         f"🔗 {project_url(pid)}\n\n"
#         f"{excerpt or 'Описание отсутствует'}"
#     )


# def process_once(state: dict[str, Any]) -> None:
#     projects = get_open_projects()
#     # Старые первыми, чтобы уведомления шли по времени.
#     for project in reversed(projects):
#         pid = str(project.get("id"))
#         if not pid or pid == "None":
#             continue
#         if pid in state["seen"]:
#             continue

#         # Сразу отмечаем как просмотренный — если дальше Telegram временно упадёт,
#         # бот не будет бесконечно спамить одним и тем же проектом.
#         state["seen"].append(pid)
#         save_state(state)

#         if not is_flutter_project(project):
#             continue

#         try:
#             send_telegram(format_project_message(project))
#         except Exception as e:
#             log.exception("Telegram ошибка для проекта %s", pid)
#             continue

#         if not AUTO_BID:
#             send_telegram("ℹ️ AUTO_BID выключен — отклик автоматически не отправлялся.")
#             continue

#         if pid in state["bid"]:
#             continue

#         ok, info = add_bid(project)
#         if ok:
#             state["bid"].append(pid)
#             save_state(state)
#             send_telegram("✅ " + info + "\n\nТекст:\n" + build_bid_comment(project))
#         else:
#             send_telegram("⚠️ Не удалось отправить отклик.\n" + info)


# def main() -> None:
#     require_settings()
#     state = load_state()
#     log.info("Бот запущен. AUTO_BID=%s, DRY_RUN=%s", AUTO_BID, DRY_RUN)

#     while True:
#         try:
#             process_once(state)
#         except KeyboardInterrupt:
#             raise
#         except Exception:
#             log.exception("Ошибка цикла")

#         time.sleep(max(30, CHECK_INTERVAL_SECONDS))

#         send_telegram(
#             "🤖 Бот запущен!\n\n"
#             "Ищу новые Flutter/Dart заказы на Freelancehunt."
#         )


# if __name__ == "__main__":
#     main()






import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# НАСТРОЙКИ
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

FREELANCEHUNT_API = "https://api.freelancehunt.com/v2"
TELEGRAM_API = "https://api.telegram.org"

STATE_FILE = BASE_DIR / "state.json"


FREELANCEHUNT_TOKEN = os.getenv(
    "FREELANCEHUNT_TOKEN",
    "",
).strip()

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
).strip()

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-6-luna",
).strip()


CHECK_INTERVAL_SECONDS = int(
    os.getenv(
        "CHECK_INTERVAL_SECONDS",
        "30",
    )
)

AUTO_SEND_AFTER_SECONDS = int(
    os.getenv(
        "AUTO_SEND_AFTER_SECONDS",
        "60",
    )
)

AUTO_BID = os.getenv(
    "AUTO_BID",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

DRY_RUN = os.getenv(
    "DRY_RUN",
    "true",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


DEFAULT_BID_AMOUNT = int(
    os.getenv(
        "DEFAULT_BID_AMOUNT",
        "5000",
    )
)

DEFAULT_BID_CURRENCY = os.getenv(
    "DEFAULT_BID_CURRENCY",
    "UAH",
).upper()

DEFAULT_DAYS = int(
    os.getenv(
        "DEFAULT_DAYS",
        "5",
    )
)

SAFE_TYPE = os.getenv(
    "SAFE_TYPE",
    "employer",
).strip()


KEYWORDS = [
    item.strip().lower()
    for item in os.getenv(
        "KEYWORDS",
        "flutter,dart,мобильное приложение,"
        "мобільний застосунок,мобільний додаток,"
        "ios android,android ios",
    ).split(",")
    if item.strip()
]


STOP_WORDS = [
    item.strip().lower()
    for item in os.getenv(
        "STOP_WORDS",
        "react native,kotlin only,swift only,"
        "unity,game,игра,гра",
    ).split(",")
    if item.strip()
]


# =========================================================
# ЛОГИ
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

log = logging.getLogger(
    "freelancehunt-bot"
)


# =========================================================
# HTTP
# =========================================================

session = requests.Session()

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
) if OPENAI_API_KEY else None


# =========================================================
# ВРЕМЕННЫЕ ПРОЕКТЫ
# =========================================================

pending: dict[str, dict[str, Any]] = {}

telegram_offset = 0


# =========================================================
# ПРОВЕРКА НАСТРОЕК
# =========================================================

def require_settings() -> None:

    missing = []

    if not FREELANCEHUNT_TOKEN:
        missing.append(
            "FREELANCEHUNT_TOKEN"
        )

    if not TELEGRAM_BOT_TOKEN:
        missing.append(
            "TELEGRAM_BOT_TOKEN"
        )

    if not TELEGRAM_CHAT_ID:
        missing.append(
            "TELEGRAM_CHAT_ID"
        )

    if not OPENAI_API_KEY:
        missing.append(
            "OPENAI_API_KEY"
        )

    if missing:
        raise RuntimeError(
            "Заполни в .env: "
            + ", ".join(missing)
        )


# =========================================================
# FREELANCEHUNT HEADERS
# =========================================================

def fh_headers() -> dict[str, str]:

    return {
        "Authorization":
            f"Bearer {FREELANCEHUNT_TOKEN}",

        "Accept-Language":
            "ru",

        "Content-Type":
            "application/json",
    }


# =========================================================
# STATE
# =========================================================

def load_state() -> dict[str, Any]:

    if not STATE_FILE.exists():

        return {
            "seen": [],
            "bid": [],
            "initialized": False,
        }

    try:

        data = json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

        data.setdefault(
            "seen",
            [],
        )

        data.setdefault(
            "bid",
            [],
        )

        data.setdefault(
            "initialized",
            False,
        )

        return data

    except Exception:

        log.exception(
            "Не удалось прочитать state.json"
        )

        return {
            "seen": [],
            "bid": [],
            "initialized": False,
        }


def save_state(
    state: dict[str, Any],
) -> None:

    state["seen"] = list(
        dict.fromkeys(
            state.get(
                "seen",
                [],
            )
        )
    )[-5000:]

    state["bid"] = list(
        dict.fromkeys(
            state.get(
                "bid",
                [],
            )
        )
    )[-5000:]

    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# =========================================================
# ТЕКСТ
# =========================================================

def strip_html(
    text: str,
) -> str:

    text = re.sub(
        r"<[^>]+>",
        " ",
        text or "",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =========================================================
# ПРОВЕРКА FLUTTER
# =========================================================

def project_text(
    project: dict[str, Any],
) -> str:

    attrs = (
        project.get(
            "attributes",
            {},
        )
        or {}
    )

    title = str(
        attrs.get(
            "name"
        )
        or ""
    )

    description = strip_html(
        str(
            attrs.get(
                "description_html"
            )
            or attrs.get(
                "description"
            )
            or ""
        )
    )

    tags = " ".join(
        str(tag)
        for tag in (
            attrs.get(
                "tags"
            )
            or []
        )
    )

    skills = (
        attrs.get(
            "skills"
        )
        or []
    )

    skill_texts = []

    for skill in skills:

        if isinstance(
            skill,
            dict,
        ):

            skill_texts.append(
                str(
                    skill.get(
                        "name"
                    )
                    or skill.get(
                        "id"
                    )
                    or ""
                )
            )

        else:

            skill_texts.append(
                str(skill)
            )

    result = " ".join(
        [
            title,
            description,
            tags,
            " ".join(
                skill_texts
            ),
        ]
    )

    return result.lower()


def is_flutter_project(
    project: dict[str, Any],
) -> bool:

    text = project_text(
        project
    )

    if any(
        stop_word in text
        for stop_word in STOP_WORDS
    ):
        return False

    return any(
        keyword in text
        for keyword in KEYWORDS
    )


# =========================================================
# ПОЛУЧЕНИЕ ПРОЕКТОВ
# =========================================================

def get_open_projects(
    max_pages: int = 3,
) -> list[dict[str, Any]]:

    projects = []

    for page in range(
        1,
        max_pages + 1,
    ):

        response = session.get(
            f"{FREELANCEHUNT_API}/projects",

            headers=fh_headers(),

            params={
                "page[number]": page
            },

            timeout=25,
        )

        if response.status_code == 429:

            retry = int(
                response.headers.get(
                    "Retry-After",
                    "30",
                )
            )

            log.warning(
                "Freelancehunt rate limit. "
                "Жду %s сек.",
                retry,
            )

            time.sleep(
                retry
            )

            continue

        response.raise_for_status()

        payload = response.json()

        projects.extend(
            payload.get(
                "data",
                [],
            )
            or []
        )

        links = (
            payload.get(
                "links",
                {},
            )
            or {}
        )

        if not links.get(
            "next"
        ):
            break

    return projects


# =========================================================
# URL
# =========================================================

def project_url(
    project_id: str | int,
) -> str:

    return (
        "https://freelancehunt.com/"
        f"project/{project_id}.html"
    )


# =========================================================
# БЮДЖЕТ
# =========================================================

def get_budget(
    project: dict[str, Any],
) -> tuple[int | None, str]:

    attrs = (
        project.get(
            "attributes",
            {},
        )
        or {}
    )

    budget = (
        attrs.get(
            "budget"
        )
        or {}
    )

    if isinstance(
        budget,
        dict,
    ):

        amount = budget.get(
            "amount"
        )

        currency = str(
            budget.get(
                "currency"
            )
            or DEFAULT_BID_CURRENCY
        ).upper()

        try:

            if (
                amount
                and int(
                    float(amount)
                ) > 0
            ):

                return (
                    int(
                        float(amount)
                    ),
                    currency,
                )

        except (
            TypeError,
            ValueError,
        ):

            pass

    return (
        None,
        DEFAULT_BID_CURRENCY,
    )


# =========================================================
# РЕЗЕРВНЫЙ ОТКЛИК
# =========================================================

def fallback_proposal(
    project: dict[str, Any],
) -> dict[str, Any]:

    budget, currency = get_budget(
        project
    )

    if budget:

        amount = min(
            budget,
            DEFAULT_BID_AMOUNT,
        )

    else:

        amount = DEFAULT_BID_AMOUNT

    attrs = (
        project.get(
            "attributes",
            {},
        )
        or {}
    )

    title = str(
        attrs.get(
            "name"
        )
        or "ваш проект"
    ).strip()

    comment = (
        f"Здравствуйте! Заинтересовал ваш проект "
        f"«{title}». "

        "Я специализируюсь на кроссплатформенной "
        "разработке мобильных приложений на Flutter "
        "и готов взять на себя реализацию задачи "
        "для Android и iOS. "

        "Аккуратно реализую интерфейс, "
        "логику приложения и при необходимости "
        "подключу Firebase, API, авторизацию "
        "и базу данных. "

        "Передам протестированную рабочую сборку "
        "и чистый код, который можно будет "
        "поддерживать и развивать дальше. "

        "Буду рад обсудить детали проекта. "
        "Подскажите, есть ли у вас готовые макеты "
        "дизайна или подробное техническое задание?"
    )

    return {
        "comment": comment,
        "amount": amount,
        "currency": currency,
        "days": DEFAULT_DAYS,
        "reasoning":
            "Использован резервный расчёт.",
    }


# =========================================================
# JSON ОТ AI
# =========================================================

def extract_json(
    text: str,
) -> dict[str, Any]:

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start == -1
        or end == -1
    ):
        raise ValueError(
            "AI не вернул JSON"
        )

    return json.loads(
        text[
            start:
            end + 1
        ]
    )


# =========================================================
# AI АНАЛИЗ
# =========================================================

def ai_make_proposal(
    project: dict[str, Any],
) -> dict[str, Any]:

    if not openai_client:

        return fallback_proposal(
            project
        )

    attrs = (
        project.get(
            "attributes",
            {},
        )
        or {}
    )

    title = str(
        attrs.get(
            "name"
        )
        or ""
    )

    description = strip_html(
        str(
            attrs.get(
                "description_html"
            )
            or attrs.get(
                "description"
            )
            or ""
        )
    )

    budget, currency = get_budget(
        project
    )

    if budget:

        budget_text = (
            f"{budget} {currency}"
        )

    else:

        budget_text = (
            "не указан"
        )


    prompt = f"""
Ты помогаешь Flutter-разработчику писать отклики
на проекты Freelancehunt.

Название проекта:
{title}

Описание:
{description[:7000]}

Бюджет заказчика:
{budget_text}


Верни ТОЛЬКО JSON такого вида:

{{
  "comment": "готовый текст отклика",
  "amount": 5000,
  "currency": "{currency}",
  "days": 5,
  "reasoning": "почему выбрана такая цена и срок"
}}


Правила для текста:

1. Начни примерно так:
Здравствуйте! Заинтересовал ваш проект «{title}».

2. Текст должен быть персональным именно под этот проект.

3. Не пиши одинаковый шаблон всем.

4. Упомяни 2-4 конкретных пункта из ТЗ заказчика.

5. Если проект связан с:
- Flutter
- Firebase
- API
- авторизацией
- Firestore
- push уведомлениями
- картами
- платежами
- админ панелью
то упомяни только реально нужные технологии.

6. Объясни, что можешь сделать Android и iOS.

7. Пиши уверенно, но не обещай того,
чего нет в задании.

8. Не пиши:
«я лучший»
«100% гарантия»
и другой спам.

9. Длина примерно 700-1300 символов.

10. В конце задай один полезный вопрос заказчику.


Цена:

11. Цена должна быть конкурентной.

12. Не завышай цену.

13. Если заказчик указал бюджет,
никогда не превышай его.

14. Для нормального понятного ТЗ
можно ориентироваться примерно на
75-95% от бюджета.

15. Если задача маленькая,
можно поставить ещё ниже.

16. Если бюджета нет:
маленькая задача:
2000-5000 UAH

средняя:
5000-12000 UAH

крупная:
12000-25000 UAH


Срок:

17. Срок должен быть максимально быстрым,
но реально выполнимым.

18. Не ставь огромный запас времени.

19. Не ставь нереалистично маленький срок.

Примерно:
маленькая задача:
1-3 дня

средняя:
3-7 дней

крупная:
7-14 дней


20. amount и days должны быть целыми числами.

21. currency оставь:
{currency}
"""


    try:

        response = (
            openai_client
            .responses
            .create(
                model=OPENAI_MODEL,
                input=prompt,
            )
        )

        data = extract_json(
            response.output_text
        )

        fallback = fallback_proposal(
            project
        )

        comment = str(
            data.get(
                "comment"
            )
            or fallback[
                "comment"
            ]
        ).strip()

        amount = int(
            data.get(
                "amount"
            )
            or fallback[
                "amount"
            ]
        )

        days = int(
            data.get(
                "days"
            )
            or fallback[
                "days"
            ]
        )

        ai_currency = str(
            data.get(
                "currency"
            )
            or currency
        ).upper()

        reasoning = str(
            data.get(
                "reasoning"
            )
            or ""
        ).strip()


        # Безопасные пределы

        days = max(
            1,
            min(
                days,
                30,
            ),
        )

        if budget:

            amount = min(
                amount,
                budget,
            )

        amount = max(
            100,
            amount,
        )


        return {
            "comment":
                strip_html(
                    comment
                )[:1500],

            "amount":
                amount,

            "currency":
                ai_currency,

            "days":
                days,

            "reasoning":
                reasoning[:500],
        }


    except Exception:

        log.exception(
            "Ошибка AI анализа"
        )

        return fallback_proposal(
            project
        )


# =========================================================
# TELEGRAM SEND
# =========================================================

def send_telegram(
    text: str,
    reply_markup: dict | None = None,
) -> dict[str, Any]:

    payload: dict[str, Any] = {

        "chat_id":
            TELEGRAM_CHAT_ID,

        "text":
            text,

        "disable_web_page_preview":
            True,
    }

    if reply_markup:

        payload[
            "reply_markup"
        ] = reply_markup


    response = session.post(

        f"{TELEGRAM_API}/"
        f"bot{TELEGRAM_BOT_TOKEN}/"
        "sendMessage",

        json=payload,

        timeout=20,
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# CALLBACK
# =========================================================

def answer_callback(
    callback_id: str,
    text: str = "",
) -> None:

    try:

        session.post(

            f"{TELEGRAM_API}/"
            f"bot{TELEGRAM_BOT_TOKEN}/"
            "answerCallbackQuery",

            json={
                "callback_query_id":
                    callback_id,

                "text":
                    text,
            },

            timeout=10,
        )

    except Exception:

        log.exception(
            "Ошибка callback"
        )


# =========================================================
# ОТПРАВКА СТАВКИ
# =========================================================

def add_bid(
    project: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[bool, str]:

    project_id = project.get(
        "id"
    )

    body = {

        "days":
            int(
                proposal[
                    "days"
                ]
            ),

        "safe_type":
            SAFE_TYPE,

        "budget": {

            "amount":
                int(
                    proposal[
                        "amount"
                    ]
                ),

            "currency":
                str(
                    proposal[
                        "currency"
                    ]
                ),
        },

        "comment":
            str(
                proposal[
                    "comment"
                ]
            )[:1500],

        "is_hidden":
            False,
    }


    if DRY_RUN:

        return (
            True,

            "DRY_RUN: "
            f"{proposal['amount']} "
            f"{proposal['currency']}, "
            f"{proposal['days']} дней. "
            "Реально ставка не отправлена."
        )


    response = session.post(

        f"{FREELANCEHUNT_API}/"
        f"projects/{project_id}/bids",

        headers=fh_headers(),

        json=body,

        timeout=25,
    )


    if response.status_code in (
        200,
        201,
    ):

        return (
            True,

            "Отклик отправлен: "
            f"{proposal['amount']} "
            f"{proposal['currency']}, "
            f"{proposal['days']} дней."
        )


    try:

        error = response.json()

    except Exception:

        error = response.text[:500]


    return (
        False,

        "Freelancehunt ответил "
        f"{response.status_code}: "
        f"{error}"
    )


# =========================================================
# ТЕКСТ В TELEGRAM
# =========================================================

def proposal_message(
    project: dict[str, Any],
    proposal: dict[str, Any],
) -> str:

    project_id = str(
        project.get(
            "id"
        )
    )

    attrs = (
        project.get(
            "attributes",
            {},
        )
        or {}
    )

    title = str(
        attrs.get(
            "name"
        )
        or "Без названия"
    )

    description = strip_html(
        str(
            attrs.get(
                "description_html"
            )
            or attrs.get(
                "description"
            )
            or ""
        )
    )

    excerpt = (
        description[:700]
        + (
            "…"
            if len(
                description
            ) > 700
            else ""
        )
    )


    return (
        "🆕 Новый Flutter-заказ\n\n"

        f"📌 {title}\n\n"

        f"🔗 {project_url(project_id)}\n\n"

        "📝 ТЗ заказчика:\n"

        f"{excerpt or 'Описание отсутствует'}\n\n"

        "🤖 Предлагаемый отклик:\n\n"

        f"{proposal['comment']}\n\n"

        f"💰 Цена: "
        f"{proposal['amount']} "
        f"{proposal['currency']}\n"

        f"⏱ Срок: "
        f"{proposal['days']} дней\n\n"

        f"💡 Почему такая оценка:\n"
        f"{proposal.get('reasoning') or 'Оценка по ТЗ.'}\n\n"

        f"⏳ Если ничего не нажать, "
        f"через {AUTO_SEND_AFTER_SECONDS} секунд "
        + (
            "будет выполнен DRY RUN."
            if DRY_RUN
            else "отклик отправится автоматически."
        )
    )


# =========================================================
# ДОБАВЛЯЕМ ПРОЕКТ В ОЖИДАНИЕ
# =========================================================

def queue_project(
    project: dict[str, Any],
) -> None:

    project_id = str(
        project.get(
            "id"
        )
    )

    proposal = ai_make_proposal(
        project
    )

    deadline = (
        time.time()
        + AUTO_SEND_AFTER_SECONDS
    )


    pending[
        project_id
    ] = {

        "project":
            project,

        "proposal":
            proposal,

        "deadline":
            deadline,
    }


    keyboard = {

        "inline_keyboard": [

            [
                {
                    "text":
                        "✅ Отправить сейчас",

                    "callback_data":
                        f"send:{project_id}",
                },

                {
                    "text":
                        "❌ Отменить",

                    "callback_data":
                        f"skip:{project_id}",
                },
            ],

            [
                {
                    "text":
                        "🔄 Новый вариант",

                    "callback_data":
                        f"regen:{project_id}",
                }
            ],
        ]
    }


    send_telegram(
        proposal_message(
            project,
            proposal,
        ),
        keyboard,
    )


# =========================================================
# ФИНАЛЬНАЯ ОТПРАВКА
# =========================================================

def finalize_bid(
    project_id: str,
    state: dict[str, Any],
    source: str,
) -> None:

    item = pending.get(
        project_id
    )


    if not item:

        return


    if project_id in state[
        "bid"
    ]:

        pending.pop(
            project_id,
            None,
        )

        return


    ok, info = add_bid(

        item[
            "project"
        ],

        item[
            "proposal"
        ],
    )


    if ok:

        state[
            "bid"
        ].append(
            project_id
        )

        save_state(
            state
        )

        send_telegram(

            "✅ "
            + info
            + "\n\n"
            + f"Источник: {source}\n\n"
            + "Текст:\n"
            + item[
                "proposal"
            ][
                "comment"
            ]
        )

        pending.pop(
            project_id,
            None,
        )


    else:

        send_telegram(
            "⚠️ Не удалось отправить ставку.\n\n"
            + info
        )

        pending.pop(
            project_id,
            None,
        )


# =========================================================
# TELEGRAM CALLBACKS
# =========================================================

def handle_callback(
    callback: dict[str, Any],
    state: dict[str, Any],
) -> None:

    callback_id = str(
        callback.get(
            "id"
        )
        or ""
    )

    data = str(
        callback.get(
            "data"
        )
        or ""
    )


    if ":" not in data:

        answer_callback(
            callback_id
        )

        return


    action, project_id = data.split(
        ":",
        1,
    )


    if action == "send":

        answer_callback(
            callback_id,
            "Отправляю",
        )

        finalize_bid(
            project_id,
            state,
            "кнопка Отправить сейчас",
        )


    elif action == "skip":

        pending.pop(
            project_id,
            None,
        )

        answer_callback(
            callback_id,
            "Отменено",
        )

        send_telegram(
            "❌ Автоотклик отменён."
        )


    elif action == "regen":

        item = pending.get(
            project_id
        )

        if not item:

            answer_callback(
                callback_id,
                "Уже неактивно",
            )

            return


        answer_callback(
            callback_id,
            "Генерирую новый текст",
        )


        proposal = ai_make_proposal(
            item[
                "project"
            ]
        )


        item[
            "proposal"
        ] = proposal

        item[
            "deadline"
        ] = (
            time.time()
            + AUTO_SEND_AFTER_SECONDS
        )


        keyboard = {

            "inline_keyboard": [

                [
                    {
                        "text":
                            "✅ Отправить сейчас",

                        "callback_data":
                            f"send:{project_id}",
                    },

                    {
                        "text":
                            "❌ Отменить",

                        "callback_data":
                            f"skip:{project_id}",
                    },
                ],

                [
                    {
                        "text":
                            "🔄 Новый вариант",

                        "callback_data":
                            f"regen:{project_id}",
                    }
                ],
            ]
        }


        send_telegram(

            "🔄 Новый вариант.\n"
            "Таймер запущен заново.\n\n"

            + proposal_message(
                item[
                    "project"
                ],
                proposal,
            ),

            keyboard,
        )


# =========================================================
# TELEGRAM КОМАНДЫ
# =========================================================

def handle_text(
    text: str,
    state: dict[str, Any],
) -> None:

    text = text.strip()


    if text == "/start":

        send_telegram(
            "🤖 Бот работает.\n\n"
            "Я отслеживаю Flutter/Dart-заказы, "
            "создаю индивидуальный отклик, "
            "рассчитываю цену и срок."
        )


    elif text == "/status":

        send_telegram(

            "✅ Бот активен\n\n"

            f"DRY_RUN={DRY_RUN}\n"

            f"AUTO_BID={AUTO_BID}\n"

            f"Ожидают решения: "
            f"{len(pending)}\n"

            f"Таймер: "
            f"{AUTO_SEND_AFTER_SECONDS} сек."
        )


    elif text.startswith(
        "/send "
    ):

        project_id = text.split(
            maxsplit=1
        )[1].strip()

        finalize_bid(
            project_id,
            state,
            "команда /send",
        )


    elif text.startswith(
        "/skip "
    ):

        project_id = text.split(
            maxsplit=1
        )[1].strip()

        pending.pop(
            project_id,
            None,
        )

        send_telegram(
            "❌ Автоотклик отменён."
        )


    elif text.startswith(
        "/price "
    ):

        parts = text.split()

        if len(parts) == 3:

            project_id = parts[1]

            if project_id in pending:

                pending[
                    project_id
                ][
                    "proposal"
                ][
                    "amount"
                ] = int(
                    parts[2]
                )

                pending[
                    project_id
                ][
                    "deadline"
                ] = (
                    time.time()
                    + AUTO_SEND_AFTER_SECONDS
                )

                send_telegram(
                    "💰 Цена изменена.\n"
                    "Таймер запущен заново."
                )


    elif text.startswith(
        "/days "
    ):

        parts = text.split()

        if len(parts) == 3:

            project_id = parts[1]

            if project_id in pending:

                pending[
                    project_id
                ][
                    "proposal"
                ][
                    "days"
                ] = max(
                    1,
                    int(
                        parts[2]
                    ),
                )

                pending[
                    project_id
                ][
                    "deadline"
                ] = (
                    time.time()
                    + AUTO_SEND_AFTER_SECONDS
                )

                send_telegram(
                    "⏱ Срок изменён.\n"
                    "Таймер запущен заново."
                )


# =========================================================
# ЧИТАЕМ TELEGRAM
# =========================================================

def poll_telegram(
    state: dict[str, Any],
) -> None:

    global telegram_offset


    try:

        response = session.get(

            f"{TELEGRAM_API}/"
            f"bot{TELEGRAM_BOT_TOKEN}/"
            "getUpdates",

            params={

                "offset":
                    telegram_offset,

                "timeout":
                    0,
            },

            timeout=10,
        )


        response.raise_for_status()


        updates = response.json().get(
            "result",
            [],
        )


        for update in updates:

            telegram_offset = max(

                telegram_offset,

                int(
                    update[
                        "update_id"
                    ]
                ) + 1,
            )


            if "callback_query" in update:

                handle_callback(

                    update[
                        "callback_query"
                    ],

                    state,
                )

                continue


            message = (
                update.get(
                    "message"
                )
                or {}
            )


            chat = (
                message.get(
                    "chat"
                )
                or {}
            )


            if str(
                chat.get(
                    "id"
                )
            ) != TELEGRAM_CHAT_ID:

                continue


            text = message.get(
                "text"
            )


            if text:

                handle_text(
                    str(text),
                    state,
                )


    except Exception:

        log.exception(
            "Ошибка Telegram"
        )


# =========================================================
# ТАЙМЕР
# =========================================================

def process_deadlines(
    state: dict[str, Any],
) -> None:

    if not AUTO_BID:
        return


    now = time.time()


    due = [

        project_id

        for project_id, item
        in pending.items()

        if item[
            "deadline"
        ] <= now
    ]


    for project_id in due:

        finalize_bid(

            project_id,

            state,

            "таймер 60 секунд",
        )


# =========================================================
# ПРОВЕРКА FREELANCEHUNT
# =========================================================

def process_freelancehunt(
    state: dict[str, Any],
) -> None:

    projects = get_open_projects()


    # При первом запуске
    # просто запоминаем старые проекты

    if not state.get(
        "initialized"
    ):

        for project in projects:

            project_id = str(
                project.get(
                    "id"
                )
            )

            if (
                project_id
                and project_id != "None"
            ):

                state[
                    "seen"
                ].append(
                    project_id
                )


        state[
            "initialized"
        ] = True


        save_state(
            state
        )


        send_telegram(

            "✅ Бот запущен.\n\n"

            "Старые проекты пропущены.\n"

            "Теперь жду новые "
            "Flutter/Dart-заказы."
        )


        return


    for project in reversed(
        projects
    ):

        project_id = str(
            project.get(
                "id"
            )
        )


        if (
            not project_id
            or project_id == "None"
        ):

            continue


        if project_id in state[
            "seen"
        ]:

            continue


        state[
            "seen"
        ].append(
            project_id
        )


        save_state(
            state
        )


        if not is_flutter_project(
            project
        ):

            continue


        log.info(
            "Найден Flutter проект %s",
            project_id,
        )


        try:

            queue_project(
                project
            )

        except Exception:

            log.exception(
                "Ошибка обработки проекта %s",
                project_id,
            )


            send_telegram(

                "⚠️ Нашёл Flutter-заказ, "
                "но возникла ошибка.\n\n"

                + project_url(
                    project_id
                )
            )


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    require_settings()

    state = load_state()


    log.info(
        "Бот запущен. "
        "AUTO_BID=%s, "
        "DRY_RUN=%s, "
        "AUTO_SEND=%s сек.",
        AUTO_BID,
        DRY_RUN,
        AUTO_SEND_AFTER_SECONDS,
    )


    send_telegram(
        "🤖 Бот успешно запущен.\n\n"
        "Ищу новые Flutter/Dart-заказы."
    )


    next_check = 0.0


    while True:

        try:

            poll_telegram(
                state
            )


            process_deadlines(
                state
            )


            now = time.time()


            if now >= next_check:

                process_freelancehunt(
                    state
                )

                next_check = (
                    now
                    + max(
                        15,
                        CHECK_INTERVAL_SECONDS,
                    )
                )


            time.sleep(
                1
            )


        except KeyboardInterrupt:

            log.info(
                "Бот остановлен."
            )

            break


        except Exception:

            log.exception(
                "Ошибка основного цикла"
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    main()