"""Генерация и проверка заданий 4 и 5 ЕГЭ.

Модуль не зависит от Django и GigaChat, поэтому его легко тестировать.
"""
import json
import random
import re

from . import bank

VOWELS = "аеёиоуыэюя"

STRESS_TASK = (
    "Укажите варианты ответов, в которых верно выделена буква, "
    "обозначающая ударный гласный звук."
)
PARONYM_TASK = (
    "В одном из приведённых ниже предложений НЕВЕРНО употреблено выделенное слово. "
    "Исправьте лексическую ошибку, подобрав к выделенному слову пароним. "
    "Запишите подобранное слово, соблюдая нормы современного русского литературного языка."
)


# ---------------------------------------------------------------------------
# Ударения
# ---------------------------------------------------------------------------
def is_valid_form(form):
    """Слово из русских букв, где ровно одна заглавная — и это гласная."""
    if not isinstance(form, str) or not re.fullmatch(r"[а-яёА-ЯЁ]{2,40}", form):
        return False
    upper = [c for c in form if c.isupper()]
    return len(upper) == 1 and upper[0].lower() in VOWELS


def stress_index(form):
    """Индекс ударной (заглавной) гласной или -1."""
    return next((i for i, c in enumerate(form) if c.isupper()), -1) if is_valid_form(form) else -1


def syllable_number(form):
    i = stress_index(form)
    return sum(1 for c in form[: i + 1] if c.lower() in VOWELS) if i >= 0 else 0


def _norm(form):
    return form.lower().replace("ё", "е")


def shift_stress(right, rng):
    """Неверный вариант: ударение переносится на другую гласную."""
    plain = right.lower()
    ri = stress_index(right)
    options = [i for i, c in enumerate(plain) if c in VOWELS and i != ri]
    j = rng.choice(options)
    chars = list(plain.replace("ё", "е"))
    chars[j] = chars[j].upper()
    return "".join(chars)


def _stress_explanation(right, correct):
    n = syllable_number(right)
    base = ("Верно: %s (ударение на %d-м слоге)." if correct
            else "Ошибка. Правильно: %s (ударение на %d-м слоге).") % (right, n)
    note = bank.STRESS_NOTES.get(right, "")
    return base + (" " + note if note else "")


def make_stress_items(n=5, rng=None):
    """Тест из банка слов: 2–3 слова с ошибкой в ударении, остальные верные."""
    rng = rng or random
    words = rng.sample(bank.STRESS_WORDS, n)
    wrong = set(rng.sample(range(n), rng.choice([2, 3])))
    items = []
    for i, right in enumerate(words):
        correct = i not in wrong
        items.append({
            "shown": right if correct else shift_stress(right, rng),
            "right": right,
            "correct": correct,
            "explanation": _stress_explanation(right, correct),
        })
    return items


def stress_items_to_text(items):
    """Текстовый формат, совместимый с прежним API: «N. слово | +/- | пояснение»."""
    return "\n".join(
        "%d. %s | %s | %s" % (i, it["shown"], "+" if it["correct"] else "-", it["explanation"])
        for i, it in enumerate(items, 1)
    )


# ---------------------------------------------------------------------------
# Паронимы
# ---------------------------------------------------------------------------
def make_paronym_items(n=5, rng=None):
    """Пять предложений, в одном из которых вместо нужного слова стоит его пароним."""
    rng = rng or random
    entries = rng.sample(bank.PARONYMS, n)
    bad_index = rng.randrange(n)
    items = []
    for i, (tpl, ok, bad, expl) in enumerate(entries):
        wrong = i == bad_index
        items.append({
            "text": tpl.format((bad if wrong else ok).upper()),
            "correct": not wrong,
            "answer": ok if wrong else "",
            "explanation": (
                "Слово употреблено неверно, нужен пароним «%s». %s" % (ok, expl) if wrong
                else "Слово употреблено верно. " + expl
            ),
        })
    return items


def paronym_items_to_text(items):
    lines = [PARONYM_TASK, ""]
    for i, it in enumerate(items, 1):
        lines.append("%d. %s | %s | %s" % (i, it["text"], "+" if it["correct"] else "-", it["explanation"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Разбор и проверка ответов ИИ
# ---------------------------------------------------------------------------
def extract_json(text):
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("В ответе нет JSON")
    return json.loads(s[start:end + 1])


def _clean(text, limit=300):
    return re.sub(r"[*#`]", "", str(text or "")).strip()[:limit]


def validate_ai_stress(data):
    raw = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw, list) or len(raw) != 5:
        raise ValueError("Нужно ровно 5 слов")
    items, seen = [], set()
    for o in raw:
        if not isinstance(o, dict):
            raise ValueError("Неверный элемент")
        shown, right = str(o.get("shown", "")).strip(), str(o.get("right", "")).strip()
        if not (is_valid_form(shown) and is_valid_form(right)):
            raise ValueError("Неверная запись слова: %r / %r" % (shown, right))
        if _norm(shown) != _norm(right):
            raise ValueError("Слова shown и right различаются")
        if _norm(right) in seen:
            raise ValueError("Повтор слова")
        seen.add(_norm(right))
        correct = shown == right
        expl = _clean(o.get("explanation"))
        head = "Верно: %s." % right if correct else "Ошибка. Правильно: %s." % right
        items.append({"shown": shown, "right": right, "correct": correct,
                      "explanation": head + (" " + expl if expl else "")})
    wrong = sum(1 for it in items if not it["correct"])
    if not 1 <= wrong <= 4:
        raise ValueError("Должна быть хотя бы одна ошибка и хотя бы одно верное слово")
    return items


def validate_ai_paronyms(data):
    raw = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw, list) or len(raw) != 5:
        raise ValueError("Нужно ровно 5 предложений")
    items = []
    for o in raw:
        if not isinstance(o, dict):
            raise ValueError("Неверный элемент")
        text = str(o.get("sentence", "")).strip()
        if len(text) > 400 or len(re.findall(r"[А-ЯЁ]{3,}", text)) != 1:
            raise ValueError("В предложении должно быть ровно одно выделенное слово")
        correct = o.get("correct") is True
        answer = str(o.get("answer", "")).strip().lower()
        if not correct and not re.fullmatch(r"[а-яё-]{3,30}", answer):
            raise ValueError("Не указан пароним для ошибочного предложения")
        items.append({"text": text, "correct": correct, "answer": "" if correct else answer,
                      "explanation": _clean(o.get("explanation"))})
    if sum(1 for it in items if not it["correct"]) != 1:
        raise ValueError("Ошибочным должно быть ровно одно предложение")
    return items


# ---------------------------------------------------------------------------
# Промпты
# ---------------------------------------------------------------------------
def stress_generation_prompt():
    return (
        "Ты — эксперт по русскому языку, составитель заданий ЕГЭ №4 (орфоэпические нормы).\n"
        "Составь 5 разных слов из орфоэпического минимума ЕГЭ (разные части речи).\n"
        "Для каждого слова дай два написания: \"shown\" — вариант, который увидит ученик, "
        "и \"right\" — правильная нормативная форма. В обоих написаниях ударный гласный "
        "пишется заглавной буквой, остальные буквы строчные.\n"
        "Ровно 2 или 3 слова должны быть показаны с НЕВЕРНЫМ ударением (shown не равно right); "
        "у остальных shown равно right. Букву «ё» сохраняй, только если на неё падает ударение.\n"
        "В \"explanation\" коротко (до 20 слов) объясни, почему ударение именно такое.\n"
        "Верни ТОЛЬКО JSON без пояснений и без ```:\n"
        "{\"items\":[{\"shown\":\"понЯв\",\"right\":\"понЯв\",\"explanation\":\"...\"}]}\n"
        "Для разнообразия ориентируйся на число %d." % random.randint(1, 10000)
    )


def paronym_generation_prompt():
    return (
        "Ты — эксперт по русскому языку, составитель заданий ЕГЭ №5 (паронимы).\n"
        "Составь 5 новых предложений. В каждом одно слово, выделенное ЗАГЛАВНЫМИ буквами "
        "(только это слово заглавными). В четырёх предложениях выделенное слово употреблено верно, "
        "ровно в одном — неверно: вместо него должен стоять его пароним.\n"
        "Для ошибочного предложения укажи в \"answer\" правильный пароним строчными буквами "
        "в той форме, в которой он должен стоять в предложении. Для верных answer — пустая строка.\n"
        "В \"explanation\" коротко (до 30 слов) объясни разницу в значении паронимов.\n"
        "Верни ТОЛЬКО JSON без пояснений и без ```:\n"
        "{\"items\":[{\"sentence\":\"В ИГОРНОМ зале было людно.\",\"correct\":false,"
        "\"answer\":\"игровом\",\"explanation\":\"...\"}]}\n"
        "Для разнообразия ориентируйся на число %d." % random.randint(1, 10000)
    )


STRESS_CHECK_PROMPT = (
    "Ты — эксперт по русскому языку и репетитор по ЕГЭ, задание 4 (постановка ударений).\n"
    "Тебе дан список слов; заглавная буква в каждом слове — ударный гласный.\n"
    "Для каждого слова напиши одну строку в формате:\n"
    "N. слово — верно/неверно. Правильно: слово с заглавной ударной. Краткое объяснение.\n"
    "Пиши обычным текстом без markdown. Если не уверен в нормативном ударении, скажи об этом честно."
)

PARONYM_CHECK_PROMPT = (
    "Ты — эксперт по русскому языку и репетитор по ЕГЭ, задание 5 (паронимы).\n"
    "Тебе даны 5 предложений; выделенное слово написано заглавными буквами. "
    "В одном из них выделенное слово употреблено неверно.\n"
    "Ответь так: номер ошибочного предложения; пароним, который нужно подставить; "
    "почему исходное слово не подходит; почему пароним подходит. "
    "Затем одной строкой укажи, почему остальные предложения верны.\n"
    "Пиши обычным текстом без markdown."
)