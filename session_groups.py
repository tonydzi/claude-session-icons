#!/usr/bin/env python3
"""session_groups.py -- раскладка сессий Claude Desktop (Code tab) по группам сайдбара, 0 LLM.

Назначение: приложение хранит группы в claude_desktop_config.json, но рычаг переноса
(ccd_sidebar.move_sessions) заперт серверным флагом 2365358358 (issue anthropics/claude-code#92621).
Пока флаг закрыт, группа живёт В ЗАГОЛОВКЕ -- с 10.09.2026 ИКОНКОЙ, а не словом:
"⚙️ Имя" / "⚙️ Р+Имя" (приказ Антона 10.09: «мало пикселей на экране, нужна иконка»).
Скрипт НЕ переименовывает (это умеет только сессия через MCP set_session_title) -- он строит ПЛАН.

Режимы:
  plan  [--limit N] [--all]  -> JSON {sid,title,group,new_title} сессий БЕЗ группы и БЕЗ иконки
  table [--limit N] -> CSV: last,final,source,group_app,tag,guess,routine,archived,title,sid
  groups            -> финальные группы + их иконки
  retag [--limit N] -> JSON {sid,title,new_title}: словесный тег [Инфра] -> иконка ⚙️
Вход: %APPDATA%/Claude (win) / ~/Library/Application Support/Claude (mac) / ~/.config/Claude (linux);
      env CLAUDE_DESKTOP_DIR переопределяет.
Кто дёргает: скилл /session-groups; /retro шаг 6a-кватер; старт сессии. Рельса: локальный python.
updated: 2026-09-10
"""
import json, io, glob, os, re, sys, csv, datetime, argparse


def app_dir():
    e = os.environ.get("CLAUDE_DESKTOP_DIR")
    if e:
        return e
    if sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], "Claude")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Claude")
    return os.path.expanduser("~/.config/Claude")


RULES = [
    ("ДРы", r"\bDR\b|ДР\b|deep research|дипрес|синтез dr|research"),
    ("$$$ Важное Кофаундер", r"продаж|платн|оффер|вакан|\bcv\b|резюме|витрин|рейз|фандрайз|инвест|кофаундер|enterprise|пилот|деньг|\$\$\$|palo-alto|marketplace|hacker news|show hn|arxiv|арxив|статья|\bhr\b|\bхр\b|cover letter|\bjob"),
    ("Лиды СРМ CRM", r"лид|crm|срм|сиренк|аутрич|outreach|фоллоуап|followup|касани|триаж|triage|\bdm\b|личк"),
    ("content", r"пост|контент|content|тизер|лонгрид|twitter|x-post|facebook|фб|\bfb\b|dev\.to|youtube|видео|майкрофт|юмор|голос и стиль|эпизод|episode|blog|substack|reddit|linkedin|threads"),
    ("2ой мозг", r"мозг|волт|vault|obsidian|\brag\b|памят|memory|эмбед|embed|whisper|lora|гоблин|клон|файнтюн|finetun|голосов|voice|transcri|brain|knowledge|концепт|relink|перелинк"),
    ("личное", r"личн|здоров|шум вентилятор|быт|семь|\bдом\b|квартир|виза|паспорт|банк|кредит"),
    ("SINK", r"inbox|инбокс|шина|\bbus\b|посылк|deploy|раскат|синк|sync|takeout"),
    ("Инфра", r"auto |авто|retro|ретро|watch|daily|nightly|weekly|скрипт|hook|хук|скилл|skill|canon|канон|claude\.md|memory\.md|версион|долг|infra|инфра|firefox|chrome|mcp|python|бэкап|backup|task|задач|сессии|session|рутин|планировщик|gate|гейт|телег|telegram|whatsapp|granola|screenpipe|worktree|\bgit|github|\bpr\b|issue|deflate|вентилятор|gpu|arch|\bhk\b|fleet|флот|маяк|хаб|hub|pipeline|конвейер|шард|pending|корень|пульт|канарейк|remote control"),
]
# Длинные имена групп приложения -> короткое имя (anton 09.09.2026 «используй ИХ именно!»)
SHORT = {
    "$$$ Важное Кофаундер": "$$$", "2ой мозг": "2мозг", "content": "content",
    "Лиды СРМ CRM": "Лиды-CRM", "Инфра": "Инфра", "ДРы": "ДРы", "личное": "личное",
    "SINK": "SINK", "03 SINK": "SINK",
}
FINAL = ["$$$", "2мозг", "content", "Лиды-CRM", "Инфра", "ДРы", "личное", "SINK"]
# ⭐ ИКОНКИ (anton 10.09.2026, голосом): в заголовке живёт ИКОНКА, не слово -- экономия пикселей.
ICON = {
    "$$$": "💰", "2мозг": "🧠", "content": "✍️", "Лиды-CRM": "🎯",
    "Инфра": "⚙️", "ДРы": "🔬", "личное": "🏠", "SINK": "📥", "?": "❓",
}
BY_ICON = {v: k for k, v in ICON.items()}
# словесный тег [имя] в первых 80 символах (старый формат, ловим ради миграции в иконку)
TAG = re.compile(r"\[([^\]]{1,40})\]")
# иконка в самом начале заголовка (допускаем мусор «!!», «+», «*» перед ней)
LEAD = re.compile(r"^[\s!+*]*(" + "|".join(re.escape(i) for i in BY_ICON) + r")️?\s*")


def short(name):
    return SHORT.get(name, name)


def tag_of(title):
    """(как_в_заголовке, нормализованное_короткое_имя). '' если метки нет либо она чужая."""
    m = LEAD.match(title)
    if m:
        g = BY_ICON[m.group(1)]
        return m.group(1), g
    m = TAG.search(title[:80])
    if not m:
        return "", ""
    raw = m.group(1).strip()
    if raw == "?":
        return "?", "?"
    s = short(raw)
    return (raw, s) if s in FINAL else ("", "")


def retitle(title, group):
    """Новый заголовок: иконка группы впереди. Снимает старую иконку/словесный тег."""
    icon = ICON.get(group, ICON["?"])
    rest = title
    m = LEAD.match(rest)
    if m:  # уже иконка -- меняем её
        head = re.match(r"^[\s!+*]*", rest).group(0).strip()
        return head + icon + " " + rest[m.end():].lstrip()
    m = TAG.search(rest[:80])
    if m and short(m.group(1).strip()) in FINAL + ["?"]:  # наш словесный тег -> иконка
        rest = (rest[:m.start()] + rest[m.end():]).replace("  ", " ")
        mm = re.match(r"^([\s!+*]*)", rest)
        return mm.group(1).strip() + icon + " " + rest[mm.end():].lstrip()
    # чужой тег ([GROWTH]) не трогаем: наша иконка встаёт перед ним
    mm = re.match(r"^([\s!+*]*)", title)
    return mm.group(1).strip() + icon + " " + title[mm.end():].lstrip()


def guess(t):
    tl = t.lower()
    for g, rx in RULES:
        if re.search(rx, tl, re.I):
            return short(g)
    return "?"


def load():
    root = app_dir()
    cfg_path = os.path.join(root, "claude_desktop_config.json")
    if not os.path.isfile(cfg_path):
        sys.exit("CONFIG-NOT-FOUND " + cfg_path + " (Claude Desktop не установлен или CLAUDE_DESKTOP_DIR неверен)")
    cfg = json.load(io.open(cfg_path, encoding="utf-8"))
    scopes = cfg["preferences"]["epitaxyPrefs"].get("dframe-group-scopes", {})
    gname, assign = {}, {}
    for v in scopes.values():
        for g in v.get("groups", []):
            gname[g["id"]] = g["name"]
        for k, gid in v.get("assignments", {}).items():
            assign[k.split(":", 1)[1]] = gname.get(gid, gid)
    rows = []
    for f in glob.glob(os.path.join(root, "claude-code-sessions", "*", "*", "local_*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        t = d.get("title") or ""
        la = int(d.get("lastActivityAt") or 0) / 1000
        raw_tag, norm_tag = tag_of(t)
        rows.append({
            "sid": d.get("sessionId"), "title": t,
            "group_app": short(assign.get(d.get("sessionId"), "")),
            "tag": norm_tag, "tag_raw": raw_tag,
            "has_icon": bool(LEAD.match(t)),
            "guess": guess(t),
            "routine": bool(d.get("scheduledTaskId")),
            "archived": bool(d.get("isArchived")),
            "last_ts": la,
            "last": datetime.datetime.fromtimestamp(la).strftime("%Y-%m-%d %H:%M") if la else "",
        })
    rows.sort(key=lambda r: r["last_ts"], reverse=True)
    for r in rows:
        r["final"] = r["group_app"] or r["tag"] or r["guess"]
        r["source"] = "app" if r["group_app"] else "tag" if r["tag"] else "guess"
    return sorted(set(gname.values())), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["plan", "table", "groups", "retag"])
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    groups, rows = load()
    if a.mode == "groups":
        for g in FINAL:
            print(ICON[g] + "  " + g)
        print(ICON["?"] + "  ? (не определено, разбирает Антон)")
        print("# в приложении: " + " · ".join(groups), file=sys.stderr)
        return 0
    if a.mode == "retag":
        # словесный тег [Инфра] -> иконка ⚙️ (миграция 10.09.2026)
        todo = [{"sid": r["sid"], "title": r["title"], "group": r["tag"],
                 "new_title": retitle(r["title"], r["tag"])}
                for r in rows if r["tag"] and not r["has_icon"] and (a.all or not r["archived"])][:a.limit]
        print(json.dumps(todo, ensure_ascii=False, indent=1))
        return 0
    if a.mode == "table":
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["last", "final", "source", "group_app", "tag", "guess", "routine", "archived", "title", "sid"])
        for r in rows[:a.limit]:
            w.writerow([r["last"], r["final"], r["source"], r["group_app"], r["tag"], r["guess"], r["routine"], r["archived"], r["title"], r["sid"]])
        return 0
    todo = [{"sid": r["sid"], "title": r["title"], "group": r["guess"], "new_title": retitle(r["title"], r["guess"])}
            for r in rows if not r["group_app"] and not r["tag"] and (a.all or not r["archived"])][:a.limit]
    print(json.dumps(todo, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
