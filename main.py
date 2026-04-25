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

US_TICKERS = ["NVDA", "AVGO", "AAPL", "GOOG", "MSFT", "GEV", "GE"]
SPECIAL_TICKERS = ["BANKS"]

US_COMPANIES = {
    "NVDA": ["nvidia", "nvda"],
    "AVGO": ["broadcom", "avgo"],
    "AAPL": ["apple", "aapl"],
    "GOOG": ["google", "alphabet", "goog"],
    "MSFT": ["microsoft", "msft"],
    "GE":   ["general electric co", "ge"],
    "GEV":  ["ge vernova inc", "gev"]
}

IL_COMPANIES = {
    "LUMI": {
        "queries": ['"בנק לאומי"', '"Bank Leumi"'],
        "aliases": ["בנק לאומי", "Bank Leumi", "Leumi"]
    },
    "POLI": {
        "queries": ['"בנק הפועלים"', '"Bank Hapoalim"'],
        "aliases": ["בנק הפועלים", "Bank Hapoalim", "Hapoalim"]
    },
    "HARL": {
        "queries": ['"הראל השקעות"', '"Harel Insurance"', '"Harel"'],
        "aliases": ["הראל השקעות", "Harel Insurance", "Harel"]
    },
    "ESLT": {
        "queries": ['"אלביט מערכות"', '"Elbit Systems"'],
        "aliases": ["אלביט מערכות", "Elbit Systems", "Elbit"]
    },
    "DLEKG": {
        "queries": ['"דלק קבוצה"', '"קבוצת דלק"', '"Delek Group"'],
        "aliases": ["דלק קבוצה", "קבוצת דלק", "Delek Group", "דלק"]
    },
    "PHOE": {
        "queries": ['"הפניקס"', '"Phoenix"'],
        "aliases": ["הפניקס", "Phoenix"]
    },
    "MZTF": {
        "queries": ['"מזרחי טפחות"', '"Mizrahi Tefahot"'],
        "aliases": ["מזרחי טפחות", "Mizrahi Tefahot"]
    },
    "BEZQ": {
        "queries": ['"בזק"', '"Bezeq"'],
        "aliases": ["בזק", "Bezeq"]
    },
    "PAZ": {
        "queries": ['"פז אנרגיה"', '"Paz"'],
        "aliases": ["פז אנרגיה", "Paz"]
    },
    "AZRG": {
        "queries": ['"קבוצת עזריאלי"', '"Azrieli"'],
        "aliases": ["קבוצת עזריאלי", "Azrieli"]
    },
    "FIBI": {
        "queries": ['"בנק הבינלאומי"', '"FIBI"', '"First International Bank"'],
        "aliases": ["בנק הבינלאומי", "FIBI", "First International Bank"]
    },
    "TEVA": {
        "queries": ['"טבע"', '"Teva"'],
        "aliases": ["טבע", "Teva"]
    },
    "MLSR": {
        "queries": ['"מליסרון"', '"Melisron"'],
        "aliases": ["מליסרון", "Melisron"]
    },
}

BANKS_KEYWORDS = [
    "בנק ישראל",
    "בנקים",
    "מדד הבנקים",
    "ת\"א בנקים",
    "ביטוח",
    "חברות ביטוח",
    "פיננסים",
    "financials"
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
    "LUMI": [r"בנק\s+לאומי", r"bank\s+leumi", r"\bleumi\b"],
    "POLI": [r"בנק\s+הפועלים", r"bank\s+hapoalim", r"\bhapoalim\b"],
    "HARL": [r"הראל\s+השקעות", r"harel\s+insurance", r"\bharel\b"],
    "ESLT": [r"אלביט\s+מערכות", r"elbit\s+systems", r"\belbit\b"],
    "DLEKG": [r"דלק\s+קבוצה", r"קבוצת\s+דלק", r"delek\s+group"],
    "PHOE": [r"הפניקס", r"\bphoenix\b"],
    "MZTF": [r"מזרחי\s*טפחות", r"mizrahi\s+tefahot"],
    "BEZQ": [r"\bבזק\b", r"\bbezeq\b"],
    "PAZ": [r"פז\s+אנרגיה", r"\bpaz\b"],
    "AZRG": [r"קבוצת\s+עזריאלי", r"\bazrieli\b"],
    "FIBI": [r"בנק\s+הבינלאומי", r"\bfibi\b", r"first\s+international\s+bank"],
    "TEVA": [r"\bטבע\b", r"\bteva\b"],
    "MLSR": [r"\bמליסרון\b", r"\bmelisron\b"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
}

POSITIVE_KEYWORDS = [
    "beats", "surges", "jumps", "rises", "record", "upgrade", "raises target",
    "strong demand", "wins", "contract", "growth", "profit rises",
    "מזנקת", "עולה", "עליות", "זכתה", "חוזה", "דוחות חזקים",
    "העלאת המלצה", "מחיר יעד גבוה", "רווח עלה", "צמיחה"
]

NEGATIVE_KEYWORDS = [
    "misses", "falls", "drops", "plunges", "downgrade", "cuts target",
    "weak demand", "lawsuit", "investigation", "warning", "profit falls",
    "נופלת", "יורדת", "נחתכת", "ירידות", "אזהרת רווח",
    "הורדת המלצה", "תביעה", "חקירה", "רווח ירד", "חולשה"
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
    if not published:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return str(published)

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

    positive = any(word.lower() in text for word in POSITIVE_KEYWORDS)
    negative = any(word.lower() in text for word in NEGATIVE_KEYWORDS)

    if positive and not negative:
        return "BUY 🟢"

    if negative and not positive:
        return "SELL 🔴"

    return "HOLD ⚪"

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

# =========================
# עיצוב הודעה
# =========================
def format_msg(ticker, title, published, link, source="", signal="HOLD ⚪", quote=None):
    flag = get_flag(ticker)
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

    return (
        f"🚨 <b>{flag} {ticker}</b>\n\n"
        f"📰 <b>{short_title}</b>"
        f"{signal_line}\n"
        f"🕒 <i>{clean_time_str(published)}</i>"
        f"{source_line}"
        f"{quote_line}\n"
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

    full_text = f"{title} {summary}"
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
        full_text = f"{item['title']} {item.get('summary', '')}"

        if is_market_news(full_text):
            item["ticker"] = "MARKET"
        elif is_banks_macro(full_text):
            item["ticker"] = "BANKS"

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
            signal = detect_signal(item["title"], item.get("summary", ""))

            if item["ticker"] not in quotes_cache:
                quotes_cache[item["ticker"]] = get_stock_quote(item["ticker"])

            quote = quotes_cache[item["ticker"]]

            msg = format_msg(
                ticker=item["ticker"],
                title=item["title"],
                published=item["time"],
                link=item["link"],
                source=item.get("source", ""),
                signal=signal,
                quote=quote
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
