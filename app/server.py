from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, os, urllib.parse, re, mimetypes, subprocess, sys, webbrowser, threading, time
from collections import Counter
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8081

HEARTBEAT_TIMEOUT_SECONDS = 30
HEARTBEAT_STARTUP_GRACE_SECONDS = 60
ACTIVE_SESSIONS = {}
ACTIVE_SESSIONS_LOCK = threading.Lock()
SERVER_STARTED_AT = time.time()
HTTP_SERVER = None


def asset_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

BASE_DIR = asset_dir()
USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CoXRaidDashboard"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = USER_DATA_DIR / "dashboard_config.json"
DEFAULT_RUNELITE_ROOT = Path.home() / ".runelite"
os.chdir(BASE_DIR)

CONFIG = {"runeliteRoot":"", "account":"", "noticeAccepted":False}

def load_config():
    global CONFIG
    if CONFIG_FILE.is_file():
        try:
            saved=json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(saved,dict):
                CONFIG.update({"runeliteRoot":saved.get("runeliteRoot") or "", "account":saved.get("account") or "", "noticeAccepted":bool(saved.get("noticeAccepted",False))})
        except Exception:
            pass
    if not CONFIG["runeliteRoot"] and DEFAULT_RUNELITE_ROOT.is_dir():
        CONFIG["runeliteRoot"]=str(DEFAULT_RUNELITE_ROOT)

def save_config():
    CONFIG_FILE.write_text(json.dumps(CONFIG,indent=2),encoding="utf-8")

def get_runelite_root():
    v=CONFIG.get("runeliteRoot") or ""
    return Path(v) if v else None

def selected_account():
    return (CONFIG.get("account") or "").strip()

load_config()

PURPLE_ITEMS = {
    "Dexterous prayer scroll",
    "Arcane prayer scroll",
    "Dragon sword",
    "Dinh's bulwark",
    "Dragon hunter crossbow",
    "Twisted buckler",
    "Ancestral hat",
    "Ancestral robe top",
    "Ancestral robe bottom",
    "Dragon claws",
    "Elder maul",
    "Kodai insignia",
    "Twisted bow",
}

KIT_NAME = "Twisted ancestral colour kit"
DUST_NAME = "Metamorphic Dust"


def discover_accounts(root=None):
    root = root or get_runelite_root()
    if not root or not root.is_dir():
        return []
    screenshots_root = root / "screenshots"
    if not screenshots_root.is_dir():
        return []
    accounts = []
    try:
        accounts = [p.name for p in screenshots_root.iterdir() if p.is_dir()]
    except OSError:
        pass
    return sorted(set(accounts), key=str.casefold)


def choose_runelite_folder():
    initial=str(DEFAULT_RUNELITE_ROOT.parent if DEFAULT_RUNELITE_ROOT.parent.exists() else Path.home())
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk(); root.withdraw(); root.attributes('-topmost',True)
        chosen=filedialog.askdirectory(title='Select your .runelite folder',initialdir=initial)
        root.destroy()
        if chosen: return Path(chosen)
    except Exception: pass
    if os.name=='nt':
        script=("$s=New-Object -ComObject Shell.Application;"
                "$f=$s.BrowseForFolder(0,'Select your .runelite folder',0,'"+initial.replace("'","''")+"');"
                "if($f){$f.Self.Path}")
        try:
            r=subprocess.run(['powershell.exe','-NoProfile','-STA','-Command',script],capture_output=True,text=True,timeout=120)
            if r.stdout.strip(): return Path(r.stdout.strip())
        except Exception: pass
    return None

def setup_state():
    root = get_runelite_root()
    accounts = discover_accounts(root)
    account = selected_account()
    exists = bool(root and root.is_dir())
    auto_scores = {}

    if account and account not in accounts:
        CONFIG["account"] = ""
        save_config()
        account = ""

    # First launch / no valid saved account:
    # choose the account whose Boss Kills screenshots best match raid data.
    if exists and accounts and not account:
        best_account, auto_scores = auto_select_best_account()
        if best_account:
            CONFIG["account"] = best_account
            save_config()
            account = best_account
        elif len(accounts) == 1:
            CONFIG["account"] = accounts[0]
            save_config()
            account = accounts[0]

    valid = bool(account and account in accounts)
    return {
        "runeliteRoot": str(root) if root else "",
        "runeliteExists": exists,
        "accounts": accounts,
        "account": account,
        "accountValid": valid,
        "needsRoot": not exists,
        "needsAccount": exists and bool(accounts) and not valid,
        "accountMatchScores": auto_scores,
        "noticeAccepted": bool(CONFIG.get("noticeAccepted", False)),
    }

def find_raid_log():
    root = get_runelite_root()
    if not root or not root.is_dir():
        raise FileNotFoundError("RuneLite folder is not configured.")

    for path in [
        root / "raid-data tracker" / "cox" / "raid_tracker_data.log",
        root / "raid-data-tracker" / "cox" / "raid_tracker_data.log",
    ]:
        if path.is_file():
            return path

    try:
        matches = [p for p in root.rglob("raid_tracker_data.log") if p.is_file()]
    except OSError:
        matches = []

    if not matches:
        raise FileNotFoundError(
            "Could not find raid_tracker_data.log under the selected .runelite folder."
        )
    return matches[0]

def clean_receiver(value):
    return (value or "").replace("\ufffd", " ").replace("  ", " ").strip()


SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SCREENSHOT_TIME_RE = re.compile(
    r"(?P<y>\d{4})[-_](?P<m>\d{2})[-_](?P<d>\d{2})"
    r"[_ T-](?P<h>\d{2})[-_.](?P<mi>\d{2})[-_.](?P<s>\d{2})"
)

def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def boss_kill_folder_for_account(account):
    root = get_runelite_root()
    if not root or not root.is_dir() or not account:
        return None

    account_dir = root / "screenshots" / account
    folder = account_dir / "Boss Kills"
    if folder.is_dir():
        return folder

    if account_dir.is_dir():
        try:
            for child in account_dir.iterdir():
                if child.is_dir() and child.name.casefold() == "boss kills":
                    return child
        except OSError:
            pass
    return None

def personal_purple_raids_from_records(records):
    """
    Return raids that appear to contain the user's personal purple.
    On first launch there is no selected account yet, so solo purple receivers
    are used as a strong indicator while specialLootInOwnName is also honored.
    """
    out = []
    for r in records:
        entries = [x for x in (r.get("specialLootEntries") or []) if x.get("kind") == "purple"]
        if not entries:
            continue

        if r.get("specialLootInOwnName"):
            out.append(r)
            continue

        # Solo raid: the unique receiver must be the player running the raid.
        if int(r.get("teamSize") or 0) == 1:
            out.append(r)

    return out

def score_account_against_raids(account, records):
    """
    Score how many Boss Kills screenshots for <account> can be verified against
    personal-purple raid records. Verification uses the same strong filename
    signals as the main screenshot matcher: KC, date, CoX, and time proximity.
    """
    folder = boss_kill_folder_for_account(account)
    if not folder:
        return 0

    index = build_screenshot_index([(account, folder)])
    if not index:
        return 0

    candidate_raids = personal_purple_raids_from_records(records)
    used = set()
    matched = 0

    def raid_date_key(ms):
        try:
            return datetime.fromtimestamp(int(ms) / 1000.0).strftime("%Y-%m-%d")
        except Exception:
            return ""

    for raid in sorted(candidate_raids, key=lambda r: int(r.get("date") or 0)):
        raid_kc = int(raid.get("kc") or 0)
        raid_date = raid_date_key(raid.get("date"))
        raid_ts = int(raid.get("date") or 0) / 1000.0

        scored = []
        for shot in index:
            if shot["rel"] in used:
                continue
            if shot["raidType"] and shot["raidType"] != "cox":
                continue

            score = 0
            verified = []

            if shot["kc"] is not None:
                if shot["kc"] != raid_kc:
                    continue
                score += 1000
                verified.append("KC")

            if shot["dateKey"]:
                if raid_date and shot["dateKey"] != raid_date:
                    continue
                score += 500
                verified.append("date")

            if shot["raidType"] == "cox":
                score += 250
                verified.append("CoX")

            delta = None
            if shot["timestamp"] and raid_ts:
                delta = abs(shot["timestamp"] - raid_ts)
                if delta <= 900:
                    score += 150
                    verified.append("time")
                elif delta <= 7200:
                    score += 50

            strong = (
                ("KC" in verified and "date" in verified)
                or ("KC" in verified and "CoX" in verified)
                or ("date" in verified and "CoX" in verified and "time" in verified)
            )
            if strong:
                scored.append((score, delta if delta is not None else 10**12, shot))

        if scored:
            scored.sort(key=lambda x: (-x[0], x[1]))
            used.add(scored[0][2]["rel"])
            matched += 1

    return matched

def auto_select_best_account():
    """
    On first launch, choose the screenshot account with the most verified
    matches to the raid data. Returns (account, score_map).
    """
    accounts = discover_accounts()
    if not accounts:
        return "", {}

    try:
        records = load_raids(skip_screenshot_attach=True)["records"]
    except Exception:
        return "", {account: 0 for account in accounts}

    scores = {account: score_account_against_raids(account, records) for account in accounts}
    best_score = max(scores.values(), default=0)

    if best_score <= 0:
        return "", scores

    # Stable tie-breaker: alphabetical.
    best_accounts = sorted(
        [account for account, score in scores.items() if score == best_score],
        key=str.casefold
    )
    return best_accounts[0], scores

def boss_kill_dirs():
    account = selected_account()
    folder = boss_kill_folder_for_account(account)
    return [(account, folder)] if account and folder else []

def infer_account(records, screenshot_dirs):
    configured=selected_account()
    if configured:
        for account,path in screenshot_dirs:
            if account.casefold()==configured.casefold(): return configured,path
        return configured,None

    r"""
    Infer <account> from solo special-loot receiver names.
    Prefer a receiver that has a matching .runelite\<account> screenshot folder.
    """
    counts = Counter()
    for r in records:
        if int(r.get("teamSize") or 0) != 1:
            continue
        for entry in r.get("specialLootEntries") or []:
            receiver = clean_receiver(entry.get("receiver"))
            if receiver:
                counts[receiver] += 1

    if not counts:
        return None, None

    by_name = {account.casefold(): (account, path) for account, path in screenshot_dirs}
    for receiver, _ in counts.most_common():
        match = by_name.get(receiver.casefold())
        if match:
            return receiver, match[1]

    # We still return the most likely account name; screenshot matching will then
    # fall back across every Boss Kills directory.
    return counts.most_common(1)[0][0], None

def screenshot_timestamp(path):
    """Extract a likely RuneLite screenshot timestamp; fall back to file mtime."""
    stem = path.stem

    # Common examples:
    # 2026-08-14_21-53-49
    # 2026-08-14 21.53.49
    # 2026-08-14_21.53.49
    patterns = [
        re.compile(
            r"(?P<y>\d{4})[-_](?P<m>\d{2})[-_](?P<d>\d{2})"
            r"[_ T-](?P<h>\d{2})[-_.:](?P<mi>\d{2})[-_.:](?P<s>\d{2})"
        ),
        re.compile(
            r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"
            r"[_-]?(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})"
        ),
    ]

    for pattern in patterns:
        match = pattern.search(stem)
        if not match:
            continue
        try:
            dt = datetime(
                int(match.group("y")),
                int(match.group("m")),
                int(match.group("d")),
                int(match.group("h")),
                int(match.group("mi")),
                int(match.group("s")),
            )
            return dt.timestamp(), "filename"
        except (ValueError, OSError):
            pass

    try:
        return path.stat().st_mtime, "mtime"
    except OSError:
        return None, "none"


def parse_boss_kill_filename(path):
    """
    Extract raid metadata from a RuneLite Boss Kills screenshot filename.

    We intentionally accept a range of naming styles. Useful signals are:
      - raid type text such as Chambers of Xeric / CoX
      - KC number
      - calendar date
      - optional timestamp
    """
    stem = path.stem
    lower = stem.casefold()

    # Raid type
    raid_type = ""
    if "chambers of xeric" in lower or "chambers_of_xeric" in lower or "cox" in lower:
        raid_type = "cox"
    elif "theatre of blood" in lower or "theater of blood" in lower or "tob" in lower:
        raid_type = "tob"
    elif "tombs of amascut" in lower or "toa" in lower:
        raid_type = "toa"

    # KC: support things like "KC 123", "KC-123", "kc_123", "(123)" near raid text.
    kc = None
    kc_patterns = [
        re.compile(r"\bkc[\s_\-:#]*(\d+)\b", re.I),
        re.compile(r"\bkill[\s_\-]*count[\s_\-:#]*(\d+)\b", re.I),
    ]
    for pat in kc_patterns:
        match = pat.search(stem)
        if match:
            try:
                kc = int(match.group(1))
                break
            except ValueError:
                pass

    # Date/time. Support YYYY-MM-DD and YYYY_MM_DD.
    date_key = None
    dt_ts = None
    dt_patterns = [
        re.compile(
            r"(?P<y>\d{4})[-_](?P<m>\d{2})[-_](?P<d>\d{2})"
            r"(?:[_ T-](?P<h>\d{2})[-_.:](?P<mi>\d{2})(?:[-_.:](?P<s>\d{2}))?)?"
        ),
        re.compile(
            r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"
            r"(?:[_-]?(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2}))?"
        ),
    ]

    for pat in dt_patterns:
        match = pat.search(stem)
        if not match:
            continue
        try:
            y = int(match.group("y"))
            mo = int(match.group("m"))
            d = int(match.group("d"))
            h = int(match.group("h") or 0)
            mi = int(match.group("mi") or 0)
            s = int(match.group("s") or 0)
            dt = datetime(y, mo, d, h, mi, s)
            date_key = dt.strftime("%Y-%m-%d")
            if match.group("h"):
                dt_ts = dt.timestamp()
            break
        except (ValueError, OSError):
            pass

    return {
        "raidType": raid_type,
        "kc": kc,
        "dateKey": date_key,
        "timestamp": dt_ts,
        "filename": stem,
    }

def build_screenshot_index(screenshot_dirs):
    items = []

    for account, folder in screenshot_dirs:
        try:
            files = list(folder.rglob("*"))
        except OSError:
            continue

        for path in files:
            if not path.is_file() or path.suffix.casefold() not in SCREENSHOT_EXTENSIONS:
                continue

            meta = parse_boss_kill_filename(path)
            ts, ts_source = screenshot_timestamp(path)

            try:
                rel = path.relative_to(get_runelite_root())
            except ValueError:
                continue

            items.append({
                "account": account,
                "path": path,
                "rel": str(rel).replace("\\", "/"),
                "timestamp": meta.get("timestamp") or ts,
                "timestampSource": "filename" if meta.get("timestamp") else ts_source,
                "raidType": meta.get("raidType") or "",
                "kc": meta.get("kc"),
                "dateKey": meta.get("dateKey"),
                "filename": meta.get("filename") or path.stem,
            })

    return items

def attach_screenshots(records):
    screenshot_dirs = boss_kill_dirs()
    inferred_account, inferred_folder = infer_account(records, screenshot_dirs)
    index = build_screenshot_index(screenshot_dirs)

    preferred = []
    if inferred_folder:
        preferred_key = str(inferred_folder).casefold()
        preferred = [
            x for x in index
            if str(x["path"].parent).casefold().startswith(preferred_key)
        ]

    used = set()
    matched = 0
    personal_purples = 0
    unmatched = []

    def raid_date_key(ms):
        try:
            return datetime.fromtimestamp(int(ms) / 1000.0).strftime("%Y-%m-%d")
        except Exception:
            return ""

    def choose_for_raid(candidates, raid):
        raid_kc = int(raid.get("kc") or 0)
        raid_date = raid_date_key(raid.get("date"))
        raid_ts = int(raid.get("date") or 0) / 1000.0

        scored = []

        for shot in candidates:
            if shot["rel"] in used:
                continue

            # Boss Kills screenshot must be a CoX screenshot if the filename
            # identifies the raid type.
            if shot["raidType"] and shot["raidType"] != "cox":
                continue

            score = 0
            verified = []

            # KC is the strongest signal.
            if shot["kc"] is not None:
                if shot["kc"] != raid_kc:
                    continue
                score += 1000
                verified.append("KC")

            # Date is also a strong verification signal.
            if shot["dateKey"]:
                if raid_date and shot["dateKey"] != raid_date:
                    continue
                score += 500
                verified.append("date")

            # If the filename explicitly identifies CoX, reward it.
            if shot["raidType"] == "cox":
                score += 250
                verified.append("CoX")

            # Timestamp proximity is a tie-breaker / fallback.
            delta = None
            if shot["timestamp"] and raid_ts:
                delta = abs(shot["timestamp"] - raid_ts)
                if delta <= 900:
                    score += 150
                    verified.append("time")
                elif delta <= 7200:
                    score += 50

            # Prefer inferred account folder.
            if inferred_account and shot["account"].casefold() == inferred_account.casefold():
                score += 100

            # Require at least a convincing filename match:
            # KC+date, or KC+CoX, or exact-date+CoX+close timestamp.
            strong = (
                ("KC" in verified and "date" in verified)
                or ("KC" in verified and "CoX" in verified)
                or ("date" in verified and "CoX" in verified and "time" in verified)
            )
            if not strong:
                continue

            scored.append((score, delta if delta is not None else 10**12, shot, verified))

        if not scored:
            return None

        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[0][2], scored[0][1], scored[0][3]

    for r in sorted(records, key=lambda x: int(x.get("date") or 0)):
        for entry in (r.get("specialLootEntries") or []):
            if entry.get("kind") != "purple":
                continue

            receiver = clean_receiver(entry.get("receiver"))
            is_personal = bool(r.get("specialLootInOwnName"))

            if inferred_account and receiver:
                is_personal = (
                    is_personal
                    or receiver.casefold() == inferred_account.casefold()
                )

            if not is_personal:
                continue

            personal_purples += 1

            selected = choose_for_raid(preferred, r) if preferred else None
            if selected is None:
                selected = choose_for_raid(index, r)

            if selected is None:
                unmatched.append({
                    "kc": r.get("kc"),
                    "loot": entry.get("name"),
                    "receiver": receiver,
                    "date": r.get("date"),
                })
                continue

            shot, delta, verified = selected
            used.add(shot["rel"])

            entry["screenshotUrl"] = (
                "/api/screenshot?rel="
                + urllib.parse.quote(shot["rel"], safe="")
            )
            entry["screenshotFile"] = shot["path"].name
            entry["screenshotAccount"] = shot["account"]
            entry["screenshotDeltaSeconds"] = round(delta, 1) if delta is not None else None
            entry["screenshotVerifiedBy"] = verified
            matched += 1

    return {
        "runeliteRoot": str(get_runelite_root() or ""),
        "inferredAccount": inferred_account or "",
        "inferredFolder": str(inferred_folder) if inferred_folder else "",
        "screenshotFolders": len(screenshot_dirs),
        "screenshotFolderPaths": [str(path) for _, path in screenshot_dirs],
        "screenshotsIndexed": len(index),
        "personalPurples": personal_purples,
        "screenshotsMatched": matched,
        "unmatchedPersonalPurples": unmatched[:20],
        "screenshotSource": "Boss Kills",
    }

def load_raids(skip_screenshot_attach=False):
    LOG_FILE=find_raid_log()
    if not LOG_FILE.exists():
        raise FileNotFoundError(f"Raid log not found: {LOG_FILE}")

    records, bad_lines = [], 0

    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue

            special_entries = []
            regular_loot = []
            regular_value = 0

            special_field = (r.get("specialLoot") or "").strip()
            special_receiver = clean_receiver(r.get("specialLootReceiver"))
            kit_receiver = clean_receiver(r.get("kitReceiver"))
            dust_receiver = clean_receiver(r.get("dustReceiver"))

            special_value_field = r.get("specialLootValue")
            special_value_field = (
                special_value_field
                if isinstance(special_value_field, (int, float)) and special_value_field > 0
                else 0
            )

            # Track recognized special drops found in lootList. This is more robust
            # than depending only on specialLoot because some tracker records put
            # the item in lootList while specialLoot is blank.
            found_special_names = set()

            for item in (r.get("lootList") or []):
                name = item.get("name") or ""
                qty = item.get("quantity") or 0
                price = item.get("price")
                price = price if isinstance(price, (int, float)) and price > 0 else 0

                if name in PURPLE_ITEMS:
                    special_entries.append({
                        "name": name,
                        "receiver": special_receiver,
                        "value": special_value_field if special_field == name and special_value_field else price,
                        "kind": "purple",
                    })
                    found_special_names.add(name)
                    continue

                if name == KIT_NAME:
                    special_entries.append({
                        "name": KIT_NAME,
                        "receiver": kit_receiver,
                        "value": price,
                        "kind": "kit",
                    })
                    found_special_names.add(name)
                    continue

                # Accept both capitalization variants in case the tracker changes it.
                if name.lower() == DUST_NAME.lower():
                    special_entries.append({
                        "name": DUST_NAME,
                        "receiver": dust_receiver,
                        "value": price,
                        "kind": "dust",
                    })
                    found_special_names.add(name)
                    continue

                regular_loot.append({"name": name, "quantity": qty, "price": price})
                regular_value += price

            # If specialLoot is populated but the item wasn't also present in lootList,
            # still add it from the dedicated fields.
            if special_field and special_field not in found_special_names:
                special_entries.insert(0, {
                    "name": special_field,
                    "receiver": special_receiver,
                    "value": special_value_field,
                    "kind": "purple",
                })

            # Handle kit/dust receiver fields even if the tracker omitted them from lootList.
            if kit_receiver and not any(x["kind"] == "kit" for x in special_entries):
                special_entries.append({
                    "name": KIT_NAME,
                    "receiver": kit_receiver,
                    "value": 0,
                    "kind": "kit",
                })

            if dust_receiver and not any(x["kind"] == "dust" for x in special_entries):
                special_entries.append({
                    "name": DUST_NAME,
                    "receiver": dust_receiver,
                    "value": 0,
                    "kind": "dust",
                })

            records.append({
                "date": r.get("date"),
                "kc": r.get("completionCount"),
                "teamSize": r.get("teamSize"),
                "challengeMode": bool(r.get("challengeMode")),
                "raidTime": r.get("raidTime"),
                "totalPoints": r.get("totalPoints"),
                "personalPoints": r.get("personalPoints"),
                "percentage": r.get("percentage"),
                "personalDeaths": r.get("personalDeathCount"),
                "specialLootInOwnName": bool(r.get("specialLootInOwnName")),
                "specialLootEntries": special_entries,
                "specialLootValue": sum((x.get("value") or 0) for x in special_entries),
                "regularLootValue": regular_value,
                "lootList": regular_loot,
                "uniqueID": r.get("uniqueID") or "",
            })

    screenshot_info = (
        attach_screenshots(records)
        if not skip_screenshot_attach
        else {
            "runeliteRoot": str(get_runelite_root() or ""),
            "inferredAccount": selected_account(),
            "screenshotFolders": 0,
            "screenshotsIndexed": 0,
            "personalPurples": 0,
            "screenshotsMatched": 0,
            "screenshotSource": "Boss Kills",
        }
    )

    return {
        "records": records,
        "recordCount": len(records),
        "skippedLines": bad_lines,
        "source": str(LOG_FILE),
        "screenshotInfo": screenshot_info,
    }


def register_heartbeat(session_id):
    if not session_id:
        return
    with ACTIVE_SESSIONS_LOCK:
        ACTIVE_SESSIONS[session_id] = time.time()

def prune_and_count_active_sessions():
    now = time.time()
    with ACTIVE_SESSIONS_LOCK:
        stale = [
            sid for sid, last_seen in ACTIVE_SESSIONS.items()
            if now - last_seen > HEARTBEAT_TIMEOUT_SECONDS
        ]
        for sid in stale:
            ACTIVE_SESSIONS.pop(sid, None)
        return len(ACTIVE_SESSIONS)

def request_server_shutdown():
    server = HTTP_SERVER
    if server is not None:
        threading.Thread(target=server.shutdown, daemon=True).start()

def heartbeat_watchdog():
    """
    Exit after all browser tabs have stopped heartbeating.

    Startup gets a grace period so the browser has time to open and load.
    After at least one tab has registered, the server shuts down once every
    session has been stale for HEARTBEAT_TIMEOUT_SECONDS.
    """
    has_seen_session = False

    while True:
        time.sleep(5)

        active = prune_and_count_active_sessions()
        if active > 0:
            has_seen_session = True
            continue

        if has_seen_session:
            request_server_shutdown()
            return

        if time.time() - SERVER_STARTED_AT > HEARTBEAT_STARTUP_GRACE_SECONDS:
            # Browser failed to open or dashboard was never reached.
            request_server_shutdown()
            return

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/heartbeat":
            query = urllib.parse.parse_qs(parsed.query)
            session_id = (query.get("session", [""])[0] or "").strip()
            register_heartbeat(session_id)
            body = json.dumps({
                "ok": True,
                "activeSessions": prune_and_count_active_sessions(),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/quit":
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            request_server_shutdown()
            return

        if parsed.path == "/api/accept-notice":
            CONFIG["noticeAccepted"] = True
            save_config()
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/setup":
            body=json.dumps(setup_state(),ensure_ascii=False).encode('utf-8')
            self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return

        if parsed.path == "/api/choose-runelite":
            chosen=choose_runelite_folder()
            if chosen and chosen.is_dir():
                CONFIG['runeliteRoot']=str(chosen); CONFIG['account']=''; save_config()
            payload=setup_state(); payload['cancelled']=not bool(chosen)
            body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
            self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return

        if parsed.path == "/api/select-account":
            q=urllib.parse.parse_qs(parsed.query); name=(q.get('name',[''])[0] or '').strip(); accounts=discover_accounts()
            if name not in accounts:
                body=json.dumps({'error':'Account folder was not found.'}).encode('utf-8'); self.send_response(400)
            else:
                CONFIG['account']=name; save_config(); body=json.dumps(setup_state(),ensure_ascii=False).encode('utf-8'); self.send_response(200)
            self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return

        if parsed.path == "/api/screenshot":
            query = urllib.parse.parse_qs(parsed.query)
            rel = query.get("rel", [""])[0]

            try:
                if not rel:
                    raise ValueError("Missing screenshot path")

                candidate = (get_runelite_root() / Path(rel)).resolve()
                root = get_runelite_root().resolve()

                # Prevent the API from being used to read arbitrary local files.
                try:
                    candidate.relative_to(root)
                except ValueError:
                    raise PermissionError("Screenshot path is outside .runelite")

                if candidate.suffix.casefold() not in SCREENSHOT_EXTENSIONS:
                    raise PermissionError("Unsupported screenshot file type")
                if not candidate.is_file():
                    raise FileNotFoundError("Screenshot not found")

                content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                body = candidate.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                body = str(exc).encode("utf-8", errors="replace")
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        if parsed.path == "/api/raids":
            try:
                state=setup_state()
                if state["needsRoot"]: raise RuntimeError("Dashboard setup is required before raid data can be loaded.")
                payload = load_raids()
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
            except Exception as exc:
                body = json.dumps({"error": str(exc), "source": str(LOG_FILE)}).encode("utf-8")
                self.send_response(500)

            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path in ("/", ""):
            self.path = "/dashboard.html"

        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        pass

def open_dashboard_browser():
    time.sleep(0.8)
    webbrowser.open(f"http://{HOST}:{PORT}")

if __name__ == "__main__":
    state=setup_state()
    if not getattr(sys, "frozen", False):
        print("CoX Raid Dashboard")
        print(f"RuneLite: {state['runeliteRoot'] or 'not configured'}")
        print(f"Account:  {state['account'] or 'not selected'}")
        print(f"Open:    http://{HOST}:{PORT}")
        print("The app exits automatically after all dashboard tabs are closed.")
        print("Press Ctrl+C to stop.")

    HTTP_SERVER = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    threading.Thread(target=heartbeat_watchdog, daemon=True).start()
    threading.Thread(target=open_dashboard_browser, daemon=True).start()

    try:
        HTTP_SERVER.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        HTTP_SERVER.server_close()
