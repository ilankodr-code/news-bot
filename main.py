# אם אתה רוצה לאפס היסטוריה לפני התחלה חדשה, תריץ פעם אחת:
# import os
# for f in ["sent_links.json", "sent_titles.json"]:
#     if os.path.exists(f):
#         os.remove(f)
#         print("deleted", f)

import os
import json
import time
import hashlib
import requests
import feedparser
import html
import re
import yfinance as yf

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# =========================
# הגדרות
# =========================
BOT_TOKEN = "8794578521:AAFcYLd_x1b1G2X5c6ipDi7qqqJMCHO3hUU"
CHAT_ID = "889613914"
CHECK_EVERY_SECONDS = 300

SENT_FILE = "sent_links.json"
TITLE_MEMORY_FILE = "sent_titles.json"

MAX_NEWS_AGE_HOURS = 24
BOT_START_TIME = datetime.now(timezone.utc)

US_TICKERS = ["NVDA", "AVGO", "AAPL", "GOOG", "MSFT", "GEV", "GE", "HOOD", "RDDT", "RKLB"]
SPECIAL_TICKERS = ["BANKS"]

US_COMPANIES = {
    "NVDA": ["nvidia", "nvda"],
    "AVGO": ["broadcom", "avgo"],
    "AAPL": ["apple", "aapl"],
    "GOOG": ["google", "alphabet", "goog"],
    "MSFT": ["microsoft", "msft"],
    "GE":   ["general electric co", "ge"],
    "GEV":  ["ge vernova inc", "gev"],
    "HOOD": ["robinhood", "hood"],
    "RDDT": ["reddit", "rddt"],
    "RKLB": ["rocket lab", "rocketlab", "rklb"]
}

IL_COMPANIES = {
    "LUMI": {
        "queries": ['"בנק לאומי"', '"לאומי"', '"לאומי למשכנתאות"', '"Bank Leumi"', '"Leumi"'],
        "aliases": ["בנק לאומי", "לאומי", "לאומי למשכנתאות", "leumi", "bank leumi"]
    },
    "POLI": {
        "queries": ['"בנק הפועלים"', '"הפועלים"', '"פועלים"', '"Bank Hapoalim"', '"Hapoalim"', '"Poalim"'],
        "aliases": ["בנק הפועלים", "הפועלים", "פועלים", "hapoalim", "poalim", "bank hapoalim"]
    },
    "HARL": {
        "queries": ['"הראל"', '"הראל השקעות"', '"הראל ביטוח"', '"קבוצת הראל"', '"Harel"'],
        "aliases": ["הראל", "הראל השקעות", "הראל ביטוח", "קבוצת הראל", "harel"]
    },
    "ESLT": {
        "queries": ['"אלביט"', '"אלביט מערכות"', '"אלביט סיסטמס"', '"Elbit"', '"Elbit Systems"'],
        "aliases": ["אלביט", "אלביט מערכות", "אלביט סיסטמס", "elbit", "elbit systems"]
    },
    "DLEKG": {
        "queries": ['"דלק"', '"קבוצת דלק"', '"דלק קבוצה"', '"דלק גרופ"', '"Delek Group"'],
        "aliases": ["דלק", "קבוצת דלק", "דלק קבוצה", "דלק גרופ", "delek", "delek group"]
    },
    "PHOE": {
        "queries": ['"הפניקס"', '"פניקס"', '"קבוצת הפניקס"', '"הפניקס השקעות"', '"הפניקס ביטוח"', '"Phoenix"', '"Phoenix Holdings"'],
        "aliases": ["הפניקס", "פניקס", "קבוצת הפניקס", "הפניקס השקעות", "הפניקס ביטוח", "phoenix", "phoenix holdings"]
    },
    "MZTF": {
        "queries": ['"מזרחי"', '"מזרחי טפחות"', '"מזרחי-טפחות"', '"בנק מזרחי"', '"בנק מזרחי טפחות"', '"Mizrahi Tefahot"'],
        "aliases": ["מזרחי", "מזרחי טפחות", "מזרחי-טפחות", "בנק מזרחי", "בנק מזרחי טפחות", "mizrahi", "mizrahi tefahot"]
    },
    "BEZQ": {
        "queries": ['"בזק"', '"קבוצת בזק"', '"Bezeq"'],
        "aliases": ["בזק", "קבוצת בזק", "bezeq"]
    },
    "PAZ": {
        "queries": ['"פז"', '"פז אנרגיה"', '"קבוצת פז"', '"Paz"'],
        "aliases": ["פז", "פז אנרגיה", "קבוצת פז", "paz"]
    },
    "AZRG": {
        "queries": ['"עזריאלי"', '"קבוצת עזריאלי"', '"קניוני עזריאלי"', '"Azrieli"'],
        "aliases": ["עזריאלי", "קבוצת עזריאלי", "קניוני עזריאלי", "azrieli"]
    },
    "FIBI": {
        "queries": ['"הבינלאומי"', '"בנק הבינלאומי"', '"הבנק הבינלאומי"', '"פיבי"', '"FIBI"', '"First International Bank"'],
        "aliases": ["הבינלאומי", "בנק הבינלאומי", "הבנק הבינלאומי", "פיבי", "fibi", "first international bank"]
    },
    "TEVA": {
        "queries": ['"טבע"', '"טבע תעשיות"', '"טבע תעשיות פרמצבטיות"', '"Teva"'],
        "aliases": ["טבע", "טבע תעשיות", "טבע תעשיות פרמצבטיות", "teva"]
    },
    "MLSR": {
        "queries": ['"מליסרון"', '"קבוצת מליסרון"', '"Melisron"'],
        "aliases": ["מליסרון", "קבוצת מליסרון", "melisron"]
    },
}

BANKS_KEYWORDS = [
    "בנק ישראל",
    "בנקים",
    "הבנקים",
    "מדד הבנקים",
    "ת\"א בנקים",
    "בנק הפועלים",
    "לאומי",
    "מזרחי טפחות",
    "הבינלאומי",

    "ביטוח",
    "חברות ביטוח",
    "חברות הביטוח",
    "מדד הביטוח",
    "הפניקס",
    "הראל",
    "כלל ביטוח",
    "מנורה מבטחים",

    "דלק",
    "קבוצת דלק",
    "נפט וגז",
    "אנרגיה",
    "מדד נפט וגז",
    "נפט",
    "נפט וגז",
    "תחנות דלק",
    "מחירי הדלק",
]
MARKET_KEYWORDS = [
    "המסחר ננעל",
    "יום המסחר",
    "ת\"א 35",
    "ת\"א 125",
    "מדד",
    "בורסה",
    "שוק",
    "המסחר נפתח",
    "closing bell",
    "market close"
]

ISRAEL_TICKERS = set(IL_COMPANIES.keys())

# טיקרים ל-yfinance עבור ישראל
IL_YF_TICKERS = {
    "LUMI": "LUMI.TA",
    "POLI": "POLI.TA",
    "HARL": "HARL.TA",
    "ESLT": "ESLT.TA",
    "DLEKG": "DLEKG.TA",
    "PHOE": "PHOE.TA",
    "MZTF": "MZTF.TA",
    "BEZQ": "BEZQ.TA",
    "PAZ": "PAZ.TA",
    "AZRG": "AZRG.TA",
    "FIBI": "FIBI.TA",
    "TEVA": "TEVA",
    "MLSR": "MLSR.TA",
}

# לוגואים / תמונות
COMPANY_IMAGES = {
    "NVDA": "https://logo.clearbit.com/nvidia.com",
    "AVGO": "https://logo.clearbit.com/broadcom.com",
    "AAPL": "https://logo.clearbit.com/apple.com",
    "GOOG": "https://logo.clearbit.com/google.com",
    "MSFT": "https://logo.clearbit.com/microsoft.com",
    "HOOD": "https://logo.clearbit.com/robinhood.com",
    "RDDT": "https://logo.clearbit.com/reddit.com",
    "RKLB": "https://logo.clearbit.com/rocketlabusa.com",

    "LUMI": "https://logo.clearbit.com/leumi.co.il",
    "POLI": "https://logo.clearbit.com/poalim.co.il",
    "HARL": "https://logo.clearbit.com/harel-group.co.il",
    "ESLT": "https://logo.clearbit.com/elbitsystems.com",
    "DLEKG": "https://logo.clearbit.com/delek-group.com",
    "PHOE": "https://logo.clearbit.com/fnx.co.il",
    "MZTF": "https://logo.clearbit.com/mizrahi-tefahot.co.il",
    "BEZQ": "https://logo.clearbit.com/bezeq.co.il",
    "PAZ": "https://logo.clearbit.com/paz.co.il",
    "AZRG": "https://logo.clearbit.com/azrieli.com",
    "FIBI": "https://logo.clearbit.com/fibi.co.il",
    "TEVA": "https://logo.clearbit.com/teva.com",
    "MLSR": "https://logo.clearbit.com/melisron.com",
}

STRICT_COMPANY_PATTERNS = {
    "LUMI": [r"בנק\s+לאומי", r"\bלאומי\b", r"לאומי\s+למשכנתאות", r"\bleumi\b", r"bank\s+leumi"],
    "POLI": [r"בנק\s+הפועלים", r"\bהפועלים\b", r"\bפועלים\b", r"\bhapoalim\b", r"\bpoalim\b", r"bank\s+hapoalim"],
    "HARL": [r"\bהראל\b", r"הראל\s+השקעות", r"הראל\s+ביטוח", r"קבוצת\s+הראל", r"\bharel\b"],
    "ESLT": [r"\bאלביט\b", r"אלביט\s+מערכות", r"אלביט\s+סיסטמס", r"\belbit\b", r"elbit\s+systems"],
    "DLEKG": [r"\bדלק\b", r"דלק\s+קבוצה", r"קבוצת\s+דלק", r"דלק\s+גרופ", r"\bdelek\b", r"delek\s+group"],
    "PHOE": [r"\bהפניקס\b", r"\bפניקס\b", r"קבוצת\s+הפניקס", r"הפניקס\s+השקעות", r"הפניקס\s+ביטוח", r"\bphoenix\b", r"phoenix\s+holdings"],
    "MZTF": [r"\bמזרחי\b", r"מזרחי\s*טפחות", r"מזרחי-טפחות", r"בנק\s+מזרחי", r"בנק\s+מזרחי\s+טפחות", r"\bmizrahi\b", r"mizrahi\s+tefahot"],
    "BEZQ": [r"\bבזק\b", r"קבוצת\s+בזק", r"\bbezeq\b"],
    "PAZ": [r"\bפז\b", r"פז\s+אנרגיה", r"קבוצת\s+פז", r"\bpaz\b"],
    "AZRG": [r"\bעזריאלי\b", r"קבוצת\s+עזריאלי", r"קניוני\s+עזריאלי", r"\bazrieli\b"],
    "FIBI": [r"\bהבינלאומי\b", r"בנק\s+הבינלאומי", r"הבנק\s+הבינלאומי", r"\bפיבי\b", r"\bfibi\b", r"first\s+international\s+bank"],
    "TEVA": [r"\bטבע\b", r"טבע\s+תעשיות", r"טבע\s+תעשיות\s+פרמצבטיות", r"\bteva\b"],
    "MLSR": [r"\bמליסרון\b", r"קבוצת\s+מליסרון", r"\bmelisron\b"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
}

POSITIVE_KEYWORDS = [
    # Analyst / targets
    "upgrade", "upgraded", "raises price target", "raised price target",
    "price target raised", "higher price target", "outperform", "overweight",
    "buy rating", "strong buy", "positive rating", "bullish",
    "העלאת מחיר יעד", "מחיר יעד גבוה", "מחיר יעד גבוה יותר",
    "העלה מחיר יעד", "מעלה מחיר יעד", "העלאת המלצה",
    "המלצת קנייה", "קנייה", "תשואת יתר", "אפסייד",
    "אפסייד גבוה", "פוטנציאל עלייה",

    # Earnings / business
    "beats estimates", "beats expectations", "better than expected",
    "record revenue", "record profit", "strong results", "strong earnings",
    "profit rises", "revenue rises", "guidance raised", "raises guidance",
    "growth", "strong demand", "margin expansion",
    "עקפה את התחזיות", "מעל התחזיות", "טוב מהצפוי",
    "דוחות חזקים", "תוצאות חזקות", "רווח עלה", "הכנסות עלו",
    "שיפור ברווח", "שיפור בהכנסות", "צמיחה", "ביקושים חזקים",
    "תחזית חיובית", "מעלה תחזית",

    # Market move / contracts
    "surges", "jumps", "rallies", "gains", "rises", "climbs",
    "contract win", "wins contract", "new contract", "deal signed",
    "partnership", "expansion",
    "מזנקת", "מזנק", "קופצת", "עולה", "מטפסת", "מתחזקת",
    "עלייה", "עליות", "זינוק", "תזנק", "צפויה לעלות",
    "זכתה בחוזה", "חוזה חדש", "הסכם חדש", "שיתוף פעולה"
]

JUNK_KEYWORDS = [
    "market research",
    "industry report",
    "forecast report",
    "global market report",
    "top stocks",
    "best stocks",
    "stocks to buy",
    "dividend stocks",
]

NEGATIVE_KEYWORDS = [
    # Analyst / targets
    "downgrade", "downgraded", "cuts price target", "cut price target",
    "price target cut", "lower price target", "underperform", "underweight",
    "sell rating", "negative rating", "bearish",
    "הורדת מחיר יעד", "מחיר יעד נמוך", "מחיר יעד נמוך יותר",
    "הוריד מחיר יעד", "חותך מחיר יעד", "הורדת המלצה",
    "המלצת מכירה", "מכירה", "תשואת חסר", "דאונסייד",
    "פוטנציאל ירידה",

    # Earnings / business
    "misses estimates", "misses expectations", "worse than expected",
    "weak results", "weak earnings", "profit falls", "revenue falls",
    "guidance cut", "cuts guidance", "weak guidance", "margin pressure",
    "פספסה את התחזיות", "מתחת לתחזיות", "חלש מהצפוי",
    "דוחות חלשים", "תוצאות חלשות", "רווח ירד", "הכנסות ירדו",
    "ירידה ברווח", "ירידה בהכנסות", "חולשה", "ביקושים חלשים",
    "תחזית שלילית", "חותכת תחזית", "אזהרת רווח",

    # Market move / legal
    "falls", "drops", "plunges", "slides", "declines", "tumbles",
    "lawsuit", "investigation", "probe", "warning",
    "נופלת", "נופל", "יורדת", "יורד", "נחלשת", "נחתכת",
    "ירידה", "ירידות", "נפילה", "תיפול", "צפויה לרדת",
    "תביעה", "חקירה", "אזהרה", "לחץ"
]
CATEGORY_KEYWORDS = {
    "Earnings": [
        "earnings", "results", "quarter", "revenue", "profit", "guidance",
        "דוחות", "תוצאות", "רווח", "הכנסות", "תחזית"
    ],
    "Analyst": [
        "analyst", "rating", "target price", "upgrade", "downgrade",
        "אנליסט", "המלצה", "מחיר יעד", "העלאת דירוג", "הורדת דירוג"
    ],
    "M&A": [
        "acquisition", "merger", "buyout", "deal",
        "רכישה", "מיזוג", "עסקה"
    ],
    "Regulation": [
        "regulation", "regulator", "approval", "license",
        "רגולציה", "רגולטור", "אישור", "רישיון"
    ],
    "Legal": [
        "lawsuit", "probe", "investigation", "court",
        "תביעה", "חקירה", "בית משפט"
    ],
    "Dividend": [
        "dividend", "buyback", "share repurchase",
        "דיבידנד", "רכישה עצמית"
    ],
    "Contract": [
        "contract", "order", "agreement", "partnership",
        "חוזה", "הזמנה", "הסכם", "שיתוף פעולה"
    ],
    "Management": [
        "ceo", "cfo", "chairman", "executive", "resigns", "appoints",
        "מנכ\"ל", "סמנכ\"ל", "יו\"ר", "מינוי", "התפטר"
    ]
}

# =========================
# שמירת כפילויות
# =========================
def load_sent():
    if not os.path.exists(SENT_FILE):
        return set()
    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent(sent):
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(sent)), f, ensure_ascii=False, indent=2)

def load_sent_titles():
    if not os.path.exists(TITLE_MEMORY_FILE):
        return set()
    try:
        with open(TITLE_MEMORY_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_sent_titles(sent_titles):
    with open(TITLE_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(sent_titles)), f, ensure_ascii=False, indent=2)

sent_links = load_sent()
sent_titles = load_sent_titles()

def normalize_link(link):
    try:
        parsed = urlparse(link)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)

        filtered_params = [
            (k, v) for k, v in query_params
            if not k.lower().startswith("utm_")
            and k.lower() not in {
                "guccounter", "guce_referrer", "guce_referrer_sig",
                "tsrc", "cmpid", "ncid", "siteid"
            }
        ]

        clean_query = urlencode(filtered_params)
        clean_path = parsed.path.rstrip("/")

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            clean_query,
            ""
        ))
        return normalized
    except Exception:
        return (link or "").strip().lower()

def make_id(ticker, title, link):
    normalized_title = re.sub(r"\s+", " ", (title or "").strip().lower())
    normalized_link = normalize_link(link)
    raw = f"{ticker}|{normalized_title}|{normalized_link}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def make_title_id(ticker, title):
    normalized_title = re.sub(r"\s+", " ", (title or "").strip().lower())
    raw = f"{ticker}|{normalized_title}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

# =========================
# טלגרם
# =========================
def send_telegram_with_image(msg, ticker):
    image_url = COMPANY_IMAGES.get(ticker)

    if image_url:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": CHAT_ID,
            "photo": image_url,
            "caption": msg,
            "parse_mode": "HTML"
        }
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

    r = requests.post(url, json=payload, timeout=20)
    print("telegram:", r.status_code)
    print(r.text)
    r.raise_for_status()

# =========================
# עיצוב עזר
# =========================
def shorten(text, max_len=180):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."

def strip_html(text):
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def get_flag(ticker):
    return "🇮🇱" if ticker in ISRAEL_TICKERS else "🇺🇸"

def clean_time_str(published):
    try:
        from dateutil import parser
        dt = parser.parse(published)
        return dt.strftime("%d-%m-%Y")
    except:
        return published[:10] if published else ""

# =========================
# זמן / תאריך
# =========================
def parse_feed(url):
    return feedparser.parse(url)

def normalize_time(entry):
    for field in ["published", "updated"]:
        value = getattr(entry, field, None)
        if value:
            return value
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_entry_datetime(entry):
    for field in ["published_parsed", "updated_parsed"]:
        value = getattr(entry, field, None)
        if value:
            try:
                return datetime(*value[:6], tzinfo=timezone.utc)
            except Exception:
                pass

    for field in ["published", "updated"]:
        value = getattr(entry, field, None)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    return None

def is_recent_entry(entry, max_age_hours=24):
    dt = parse_entry_datetime(entry)
    if not dt:
        return False

    now = datetime.now(timezone.utc)

    # תנאי 1: בתוך 24 שעות
    if not (timedelta(hours=0) <= (now - dt) <= timedelta(hours=max_age_hours)):
        return False

    # תנאי 2: רק אחרי שהבוט עלה
    if dt < BOT_START_TIME:
        return False

    return True

# =========================
# רלוונטיות חברה
# =========================
def company_is_relevant_us(ticker, text):
    text = strip_html(text).lower()
    title = text.split("||TITLE||")[-1] if "||TITLE||" in text else text

    aliases = US_COMPANIES.get(ticker, [])

    # חייב להופיע אחד מהשמות בכותרת עצמה
    return any(alias.lower() in title for alias in aliases)

def company_is_relevant_israel(ticker, text):
    text = strip_html(text).lower()

    aliases = [a.lower() for a in IL_COMPANIES.get(ticker, {}).get("aliases", [])]
    if any(alias in text for alias in aliases):
        return True

    patterns = STRICT_COMPANY_PATTERNS.get(ticker, [])
    if any(re.search(pattern.lower(), text) for pattern in patterns):
        return True

    return False
    
def detect_signal(title, summary=""):
    text = f"{title} {summary}".lower()

    positive_hits = []
    negative_hits = []

    for word in POSITIVE_KEYWORDS:
        if word.lower() in text:
            positive_hits.append(word)

    for word in NEGATIVE_KEYWORDS:
        if word.lower() in text:
            negative_hits.append(word)

    score = len(positive_hits) - len(negative_hits)

    if score >= 2:
        return "STRONG BUY 🔥", positive_hits

    if score == 1:
        return "BUY", positive_hits

    if score <= -2:
        return "STRONG SELL 🔥", negative_hits

    if score == -1:
        return "SELL", negative_hits

    return "HOLD", []

def detect_multiple_tickers(text):
    text = strip_html(text).lower()
    found = []

    # US - מדויק, כדי ש-GE לא ייתפס בתוך מילים כמו mortgage
    for ticker, aliases in US_COMPANIES.items():
        for alias in aliases:
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, text):
                found.append(ticker)
                break

    # Israel
    for ticker, data in IL_COMPANIES.items():
        if any(alias.lower() in text for alias in data.get("aliases", [])):
            found.append(ticker)

    return list(set(found))

def detect_category(title, summary=""):
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return category
    return "General"

def is_banks_macro(text):
    text = strip_html(text).lower()
    return any(keyword.lower() in text for keyword in BANKS_KEYWORDS)

def detect_israeli_ticker(text):
    text = strip_html(text).lower()

    for ticker, data in IL_COMPANIES.items():
        for alias in data.get("aliases", []):
            if alias.lower() in text:
                return ticker

    return None
    
def is_market_news(text):
    text = strip_html(text).lower()
    return any(keyword.lower() in text for keyword in MARKET_KEYWORDS)
    
# =========================
# מחיר מניה
# =========================
def get_stock_quote(ticker):
    try:
        yf_symbol = IL_YF_TICKERS.get(ticker, ticker)

        stock = yf.Ticker(yf_symbol)
        data = stock.history(period="2d", interval="1d")

        if data.empty:
            return None

        price = float(data["Close"].iloc[-1])

        if len(data) >= 2:
            prev_close = float(data["Close"].iloc[-2])
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
        else:
            open_price = float(data["Open"].iloc[-1])
            change_pct = ((price - open_price) / open_price) * 100 if open_price != 0 else 0.0

        return {
            "price": f"{price:.2f}",
            "change_pct": f"{change_pct:+.2f}%"
        }
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return None

def get_price_target(ticker, quote=None):
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None

    url = f"https://finnhub.io/api/v1/stock/price-target?symbol={ticker}&token={api_key}"

    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        print("FINNHUB PRICE TARGET DATA:", ticker, data)

        mean = data.get("targetMean")
        high = data.get("targetHigh")
        low = data.get("targetLow")

        upside = None
        if quote and mean:
            price = quote.get("price")
            if price:
                price = float(price)
                upside = ((float(mean) - price) / price) * 100

        if mean:
            return {
                "mean": mean,
                "high": high,
                "low": low,
                "upside": upside
            }

    except Exception as e:
        print("Price target error:", e)

    return None

def get_analyst_recommendation(ticker):
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None

    url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={api_key}"

    try:
        res = requests.get(url, timeout=5)
        data = res.json()

        if not data:
            return None

        latest = data[0]

        return {
            "strong_buy": latest.get("strongBuy", 0),
            "buy": latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0),
            "strong_sell": latest.get("strongSell", 0),
        }

    except Exception as e:
        print("Analyst recommendation error:", e)
        return None

# =========================
# עיצוב הודעה
# =========================
def format_msg(ticker, title, published, link, source="", signal="HOLD ⚪", quote=None, price_target=None, tickers=None, reasons=None, analyst_data=None):
    flag = get_flag(ticker)

    if tickers:
        ticker_display = " / ".join(tickers)
    else:
        ticker_display = ticker

    short_title = html.escape(shorten(title, 160))
    safe_link = html.escape(link, quote=True)
    safe_source = html.escape(source) if source else ""
    safe_signal = html.escape(signal)

    source_line = f"\n🏷️ <b>Source:</b> {safe_source}" if safe_source else ""
    signal_line = f"\n📊 <b>Signal:</b> {safe_signal}"


    quote_line = ""
    if quote:
        price = quote.get("price")
        change_pct = quote.get("change_pct")
        if price and change_pct:
            quote_line = f"\n📈 <b>Price:</b> {price} ({change_pct})"
        elif price:
            quote_line = f"\n📈 <b>Price:</b> {price}"
            
    analyst_line = ""
    if analyst_data:
        b = analyst_data.get("buy", 0)
        s = analyst_data.get("sell", 0)

        analyst_line = f"\n👨‍💼 <b>Analysts:</b> B:{b} | S:{s}"
    
    target_line = ""
    if price_target:
        mean = price_target.get("mean")
        upside = price_target.get("upside")

        if mean and upside is not None:
            target_line = f"\n🎯 <b>Target:</b> {mean} | Upside: {upside:+.1f}%"
        elif mean:
            target_line = f"\n🎯 <b>Target:</b> {mean}"

    return (
        f"🚨 <b>{flag} {ticker_display}</b>\n\n"
        f"📰 <b>{short_title}</b>"
        f"{signal_line}"
        f"\n🕒 <i>{clean_time_str(published)}</i>"
        f"{source_line}"
        f"{quote_line}"
        f"{analyst_line}"
        f"{target_line}\n"
        f"🔗 <a href=\"{safe_link}\">לקריאת הכתבה</a>"
    )
        
# =========================
# אמריקאיות - Yahoo Finance RSS
# =========================
def get_yahoo_news_for_ticker(ticker):
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    feed = parse_feed(url)
    items = []

    print(f"Checking Yahoo for {ticker} - entries: {len(feed.entries)}")

    for entry in feed.entries[:9]:
        if not is_recent_entry(entry, MAX_NEWS_AGE_HOURS):
            continue

        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "").strip()
        published = normalize_time(entry)

        if not title or not link:
            continue

        full_text = f"{summary} ||TITLE|| {title}"

        if not company_is_relevant_us(ticker, full_text):
            continue

        uid = make_id(ticker, title, link)
        title_uid = make_title_id(ticker, title)

        if uid in sent_links or title_uid in sent_titles:
            continue

        sent_links.add(uid)
        sent_titles.add(title_uid)

        items.append({
            "ticker": ticker,
            "title": title,
            "summary": summary,
            "time": published,
            "link": link,
            "source": "Yahoo Finance"
        })

    return items

# =========================
# ישראליות - MAYA
# =========================
def get_maya_news():
    url = "https://maya.tase.co.il/rss/CompanyReports"
    feed = parse_feed(url)
    items = []

    print(f"Checking MAYA - entries: {len(feed.entries)}")

    for entry in feed.entries[:400]:
        if not is_recent_entry(entry, MAX_NEWS_AGE_HOURS):
            continue

        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "").strip()
        link = getattr(entry, "link", "").strip()
        published = normalize_time(entry)

        if not title or not link:
            continue

        full_text = f"{title} {summary}".lower()

        for ticker in IL_COMPANIES.keys():
            if company_is_relevant_israel(ticker, full_text):
                uid = make_id(ticker, title, link)
                title_uid = make_title_id(ticker, title)

                if uid in sent_links or title_uid in sent_titles:
                    break

                sent_links.add(uid)
                sent_titles.add(title_uid)

                items.append({
                    "ticker": ticker,
                    "title": title,
                    "summary": summary,
                    "time": published,
                    "link": link,
                    "source": "MAYA"
                })
                break

    print("MAYA matched items:", len(items))
    return items

def get_globes_news():
    url = "https://www.globes.co.il/rss/news.xml"
    feed = parse_feed(url)
    items = []

    for entry in feed.entries[:10]:
        if not is_recent_entry(entry, MAX_NEWS_AGE_HOURS):
            continue

        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "").strip()
        published = normalize_time(entry)

        if not title or not link:
            continue

        items.append({
            "ticker": "IL_MARKET",
            "title": title,
            "summary": summary,
            "time": published,
            "link": link,
            "source": "Globes"
        })

    return items

def get_sponser_news():
    url = "https://www.sponser.co.il/Content_rss.aspx"
    feed = parse_feed(url)
    items = []

    print(f"Checking Sponser - entries: {len(feed.entries)}")

    for entry in feed.entries[:30]:
        if not is_recent_entry(entry, MAX_NEWS_AGE_HOURS):
            continue

        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "").strip()
        published = normalize_time(entry)

        if not title or not link:
            continue

        full_text = f"{title} {summary} {link}"

        if not (
            detect_multiple_tickers(full_text)
            or is_banks_macro(full_text)
            or is_market_news(full_text)
        ):
            continue

        items.append({
            "ticker": "IL_MARKET",
            "title": title,
            "summary": summary,
            "time": published,
            "link": link,
            "source": "Sponser"
        })

    return items
    
# =========================
# Google News RSS
# =========================
def google_news_rss(query):
    url = "https://news.google.com/rss/search"
    params = {
        "q": query,
        "hl": "he",
        "gl": "IL",
        "ceid": "IL:he"
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.text)

def get_israeli_site_news():
    items = []

    for ticker, data in IL_COMPANIES.items():
        queries = []
        for company_query in data["queries"]:
            queries.extend([
                (f'{company_query} site:bizportal.co.il', "Bizportal"),
                (f'{company_query} site:calcalist.co.il', "Calcalist"),
                (f'{company_query} site:globes.co.il', "Globes"),
            ])

        for q, source_name in queries:
            try:
                feed = google_news_rss(q)
                print(f"Checking {source_name} for {ticker} - entries: {len(feed.entries)}")

                for entry in feed.entries[:30]:
                    if not is_recent_entry(entry, MAX_NEWS_AGE_HOURS):
                        continue

                    title = getattr(entry, "title", "").strip()
                    summary = getattr(entry, "summary", "").strip()
                    link = getattr(entry, "link", "").strip()
                    published = normalize_time(entry)

                    if not title or not link:
                        continue

                    full_text = f"{title} {summary}".lower()
                    if not company_is_relevant_israel(ticker, full_text):
                        continue

                    uid = make_id(ticker, title, link)
                    title_uid = make_title_id(ticker, title)

                    if uid in sent_links or title_uid in sent_titles:
                        continue

                    sent_links.add(uid)
                    sent_titles.add(title_uid)

                    items.append({
                        "ticker": ticker,
                        "title": title,
                        "summary": summary,
                        "time": published,
                        "link": link,
                        "source": source_name
                    })

            except Exception as e:
                print(f"Google News error for {ticker} / {source_name}: {e}")

            time.sleep(0.25)

    print("Israeli site matched items:", len(items))
    return items

# =========================
# סריקה
# =========================
def scan_once():
    all_items = []

    # US
    for ticker in US_TICKERS:
        try:
            items = get_yahoo_news_for_ticker(ticker)
            all_items.extend(items)
        except Exception as e:
            print(f"Yahoo error for {ticker}:", e)

    # MAYA
    try:
        maya_items = get_maya_news()
        all_items.extend(maya_items)
        print("After MAYA:", len(all_items))
    except Exception as e:
        print("MAYA error:", e)

        # Sponser
    try:
        sponser_items = get_sponser_news()
        all_items.extend(sponser_items)
        print("After Sponser:", len(all_items))
    except Exception as e:
        print("Sponser error:", e)
        
    # Globes
    try:
        globes_items = get_globes_news()
        all_items.extend(globes_items)
        print("After Globes:", len(all_items))
    except Exception as e:
        print("Globes error:", e)

    # Israeli sites
    try:
        israeli_site_items = get_israeli_site_news()
        all_items.extend(israeli_site_items)
        print("After Israeli sites:", len(all_items))
    except Exception as e:
        print("Israeli sites error:", e)

    seen_local = set()
    unique_items = []

    for item in all_items:
        full_text = f"{item['title']} {item.get('summary', '')} {item.get('link', '')}"

        if any(junk in full_text.lower() for junk in JUNK_KEYWORDS):
            continue

        tickers = detect_multiple_tickers(full_text)

        if tickers:
            item["tickers"] = tickers
            item["ticker"] = tickers[0]

        if is_banks_macro(full_text):
            item["ticker"] = "BANKS"
        elif is_market_news(full_text):
            item["ticker"] = "MARKET"

        normalized_title = re.sub(r"[^a-zA-Z0-9א-ת ]", "", item["title"].lower())
        normalized_title = re.sub(r"\s+", " ", normalized_title).strip()

        key = (item["ticker"], normalized_title)

        if key in seen_local:
            continue

        seen_local.add(key)
        unique_items.append(item)

    print("Total new items found:", len(unique_items))

    MAX_MESSAGES_PER_SCAN = 5
    unique_items = unique_items[:MAX_MESSAGES_PER_SCAN]

    quotes_cache = {}

    for item in unique_items:
        try:
            signal, reasons = detect_signal(item["title"], item.get("summary", ""))

            if item["ticker"] not in quotes_cache:
                quotes_cache[item["ticker"]] = get_stock_quote(item["ticker"])

            quote = quotes_cache[item["ticker"]]

            price_target = get_price_target(item["ticker"], quote)
            analyst_data = get_analyst_recommendation(item["ticker"])

            msg = format_msg(
                ticker=item["ticker"],
                title=item["title"],
                published=item["time"],
                link=item["link"],
                source=item.get("source", ""),
                signal=signal,
                reasons=reasons,
                quote=quote,
                analyst_data=analyst_data,
                price_target=price_target,
                tickers=item.get("tickers")
            )

            send_telegram_with_image(msg, item["ticker"])

        except Exception as e:
            print("Send error:", e)

    save_sent(sent_links)
    save_sent_titles(sent_titles)
    print("Scan finished.")
# =========================
# ריצה רציפה
# =========================
def run_forever():
    print("Bot started and running.")
    
    while True:
        try:
            scan_once()
        except Exception as e:
            print("Loop error:", e)

        print(f"Sleeping for {CHECK_EVERY_SECONDS} seconds...")
        time.sleep(CHECK_EVERY_SECONDS)

run_forever()
