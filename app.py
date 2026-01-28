import os
import sys
import json
import datetime
import mimetypes
from collections import Counter
from django.conf import settings
from django.core.management import execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.urls import path, re_path
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve

# 1. PROJE AYARLARI
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')  # <--- KRİTİK AYAR
ASSETS_DIR = os.path.join(DIST_DIR, 'assets')

# Dosya Yolları
DECISIONS_FILE = os.path.join(BASE_DIR, 'decisions.json')
LOGS_FILE = os.path.join(BASE_DIR, 'access_logs.json')
ANNOUNCEMENTS_FILE = os.path.join(BASE_DIR, 'announcements.json')
MESSAGES_FILE = os.path.join(BASE_DIR, 'messages.json')
PASSWORDS_FILE = os.path.join(BASE_DIR, 'passwords.json')

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='gizli-anahtar-super-gizli',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'corsheaders',
        ],
        MIDDLEWARE=[
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.common.CommonMiddleware',
        ],
        CORS_ALLOW_ALL_ORIGINS=True,
        STATIC_URL='/static/',
    )

# 2. GLOBAL VERİTABANI VE YÜKLEME
ACADEMICIANS_BY_NAME = {}
ACADEMICIANS_BY_EMAIL = {}
PROJECTS_DB = {}
MATCHES_DB = []
FEEDBACK_DB = []
ACCESS_LOGS = []
ANNOUNCEMENTS = []
MESSAGES = []
PASSWORDS_DB = {}

def load_data():
    global ACADEMICIANS_BY_NAME, ACADEMICIANS_BY_EMAIL, PROJECTS_DB, MATCHES_DB, FEEDBACK_DB, ACCESS_LOGS, ANNOUNCEMENTS, MESSAGES, PASSWORDS_DB
    
    # Basit JSON yükleyiciler
    for path, var in [(DECISIONS_FILE, 'FEEDBACK_DB'), (LOGS_FILE, 'ACCESS_LOGS'),
                      (ANNOUNCEMENTS_FILE, 'ANNOUNCEMENTS'), (MESSAGES_FILE, 'MESSAGES'),
                      (PASSWORDS_FILE, 'PASSWORDS_DB')]:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: globals()[var] = json.load(f)
            except: pass

    # Akademisyenler
    path = os.path.join(BASE_DIR, 'academicians_merged.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for p in json.load(f):
                    if p.get("Fullname"): ACADEMICIANS_BY_NAME[p["Fullname"].strip().upper()] = p
                    if p.get("Email"): ACADEMICIANS_BY_EMAIL[p["Email"].strip().lower()] = p
        except: pass

    # Projeler
    path = os.path.join(BASE_DIR, 'eu_projects_merged_tum.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for p in json.load(f):
                    pid = str(p.get("project_id", "")).strip()
                    if pid: PROJECTS_DB[pid] = p
        except: pass
    
    # Eşleşmeler
    path = os.path.join(BASE_DIR, 'n8n_akademisyen_proje_onerileri.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                combined = []
                if isinstance(raw, dict): combined = [item for sublist in raw.values() if isinstance(sublist, list) for item in sublist]
                elif isinstance(raw, list): combined = raw
                
                for item in combined:
                    name = item.get('data') or item.get('academician_name')
                    pid = str(item.get('Column3') or item.get('project_id') or "")
                    if name and pid and name != "academician_name":
                        MATCHES_DB.append({
                            "name": name.strip(), "projId": pid,
                            "score": int(item.get('Column7') or item.get('score') or 0),
                            "reason": item.get('Column6') or item.get('reason') or ""
                        })
        except: pass

load_data()

# 3. YARDIMCI FONKSİYONLAR
def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def log_access(name, role, action):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ACCESS_LOGS.insert(0, {"timestamp": now, "name": name, "role": role, "action": action})
        if len(ACCESS_LOGS) > 500: ACCESS_LOGS.pop()
        save_json(LOGS_FILE, ACCESS_LOGS)
    except: pass

# --- AKILLI DOSYA SUNUCUSU ---
def serve_react(request, resource=""):
    # 1. Önce 'dist' klasörüne bak (vite.svg, logo vb. için)
    if resource:
        file_path = os.path.join(DIST_DIR, resource)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(open(file_path, 'rb'))
            
    # 2. Bulamazsa 'index.html' gönder (Siteyi aç)
    try:
        return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except FileNotFoundError:
        return HttpResponse(f"HATA: dist/index.html bulunamadı.<br>Mevcut Konum: {os.getcwd()}", status=503)

def serve_image(request, image_name):
    # Ana dizindeki images klasörüne bakar
    path = os.path.join(BASE_DIR, 'images', image_name)
    if os.path.exists(path): return FileResponse(open(path, 'rb'))
    return HttpResponse("Resim bulunamadı", 404)

def serve_academician_photo(request, image_name):
    path = os.path.join(BASE_DIR, 'akademisyen_fotograflari', image_name)
    if os.path.exists(path): return FileResponse(open(path, 'rb'))
    return HttpResponse("Fotoğraf bulunamadı", 404)

# --- API ENDPOINTLERİ (SLASH DUYARLILIĞI KALDIRILDI) ---
@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            u = d.get('username', '').strip()
            p = d.get('password', '').strip()
            
            # Admin Girişi
            if u == "admin" and p == "12345":
                log_access("Admin", "Yönetici", "Giriş Başarılı")
                return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})
                
            # Akademisyen Girişi
            acc = ACADEMICIANS_BY_EMAIL.get(u.lower())
            if acc:
                stored = PASSWORDS_DB.get(u.lower())
                real_pass = stored if stored else u.lower().split('@')[0]
                if p == real_pass:
                    log_access(acc["Fullname"], "Akademisyen", "Giriş Başarılı")
                    return JsonResponse({"status": "success", "role": "academician", "name": acc["Fullname"]})
            
            return JsonResponse({"status": "error", "message": "Giriş başarısız"}, status=401)
        except Exception as e: return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({}, status=405)

# Diğer API'ler
@csrf_exempt
def api_logout(request): return JsonResponse({"status": "success"})
@csrf_exempt
def api_list_admin(request):
    stats = {}
    for m in MATCHES_DB:
        nk = m["name"]
        if nk not in stats:
            det = ACADEMICIANS_BY_NAME.get(nk.upper(), {})
            stats[nk] = {
                "name": nk, "email": det.get("Email", "-"), "title": det.get("Title", "Akademisyen"),
                "project_count": 0, "best_score": 0, "image": det.get("Image"), "total_rating": 0, "rating_count": 0
            }
        stats[nk]["project_count"] += 1
        if m["score"] > stats[nk]["best_score"]: stats[nk]["best_score"] = m["score"]
    for fb in FEEDBACK_DB:
        name = fb.get("academician")
        rating = fb.get("rating", 0)
        if name in stats and rating > 0:
            stats[name]["total_rating"] += rating
            stats[name]["rating_count"] += 1
    final_list = []
    for s in stats.values():
        avg = 0
        if s["rating_count"] > 0: avg = round(s["total_rating"] / s["rating_count"], 1)
        s["average_rating"] = avg
        final_list.append(s)
    return JsonResponse({
        "academicians": final_list, "feedbacks": FEEDBACK_DB, "logs": ACCESS_LOGS, "announcements": ANNOUNCEMENTS
    }, safe=False)

@csrf_exempt
def api_profile(request):
    if request.method == 'POST':
        req_name = json.loads(request.body).get('name')
        raw_profile = ACADEMICIANS_BY_NAME.get(req_name.upper(), {})
        profile = {
            "Fullname": req_name, "Email": raw_profile.get("Email", "-"), "Description": raw_profile.get("Description", ""),
            "Field": raw_profile.get("Field", "-"), "Phone": raw_profile.get("Phone", "-"), "Image": raw_profile.get("Image"),
            "Title": raw_profile.get("Title", "Öğretim Üyesi"), "Duties": raw_profile.get("Duties", [])
        }
        p_matches = [m for m in MATCHES_DB if m["name"] == req_name]
        enriched = []
        for m in p_matches:
            pd = PROJECTS_DB.get(m["projId"], {})
            stat, note, rating = "waiting", "", 0
            for fb in FEEDBACK_DB:
                if fb["academician"] == req_name and fb["projId"] == m["projId"]:
                    stat = fb["decision"]; note = fb.get("note", ""); rating = fb.get("rating", 0); break
            collaborators = []
            for fb in FEEDBACK_DB:
                if fb["projId"] == m["projId"] and fb["decision"] == "accepted" and fb["academician"] != req_name:
                    collaborators.append(fb["academician"])
            project_title = pd.get("title")
            if not project_title or project_title == "Nan": project_title = pd.get("acronym") or f"Proje-{m['projId']}"
            enriched.append({
                "id": m["projId"], "score": m["score"], "reason": m["reason"], "title": project_title,
                "objective": pd.get("objective", ""), "budget": pd.get("overall_budget", "-"), "status": pd.get("status", "-"),
                "url": pd.get("url", "#"), "decision": stat, "note": note, "rating": rating, "collaborators": collaborators
            })
        enriched.sort(key=lambda x: x['score'], reverse=True)
        return JsonResponse({"profile": profile, "projects": enriched})
    return JsonResponse({}, 400)

@csrf_exempt
def api_project_decision(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            acc = d.get("academician"); pid = d.get("projId"); dec = d.get("decision")
            title = d.get("projectTitle"); note = d.get("note", ""); rating = d.get("rating", 0)
            found = False
            for item in FEEDBACK_DB:
                if item["academician"] == acc and item["projId"] == pid:
                    item["decision"] = dec; item["note"] = note; item["rating"] = int(rating)
                    item["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M"); found = True; break
            if not found:
                FEEDBACK_DB.append({
                    "academician": acc, "projId": pid, "projectTitle": title, "decision": dec,
                    "note": note, "rating": int(rating), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            save_json(DECISIONS_FILE, FEEDBACK_DB)
            return JsonResponse({"status": "success"})
        except Exception as e: return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({}, 405)

def api_top_projects(request):
    cnt = Counter(m['projId'] for m in MATCHES_DB).most_common(50)
    top = []
    for pid, c in cnt:
        pd = PROJECTS_DB.get(pid, {})
        top.append({
            "id": pid, "count": c, "title": pd.get("title") or pd.get("acronym") or f"Proje-{pid}",
            "budget": pd.get("overall_budget", "-"), "status": pd.get("status", "-"),
            "coordinated_by": pd.get("coordinated_by", "-"), "url": pd.get("url", "#")
        })
    return JsonResponse(top, safe=False)

def api_network_graph(request):
    target_user_name = request.GET.get('user')
    nodes = []; links = []; existing_node_ids = set()
    if not target_user_name: return JsonResponse({"nodes": [], "links": []}, safe=False)
    user_details = ACADEMICIANS_BY_NAME.get(target_user_name.upper())
    if user_details:
        nodes.append({"id": user_details["Fullname"], "img": user_details.get("Image"), "isCenter": True, "val": 3})
        existing_node_ids.add(user_details["Fullname"])
    else: return JsonResponse({"nodes": [], "links": []}, safe=False)
    my_accepted_projects = set()
    for fb in FEEDBACK_DB:
        if fb.get("academician") == user_details["Fullname"] and fb.get("decision") == "accepted":
            my_accepted_projects.add(fb.get("projId"))
    collaborators = set()
    for fb in FEEDBACK_DB:
        other_user = fb.get("academician"); proj_id = fb.get("projId")
        if other_user != user_details["Fullname"] and fb.get("decision") == "accepted" and proj_id in my_accepted_projects:
            collaborators.add(other_user)
    for col_name in collaborators:
        if col_name not in existing_node_ids:
            col_details = ACADEMICIANS_BY_NAME.get(col_name.upper(), {})
            nodes.append({"id": col_name, "img": col_details.get("Image"), "isCenter": False, "val": 1})
            existing_node_ids.add(col_name)
        link_exists = any(((l['source'] == user_details["Fullname"] and l['target'] == col_name) or
                           (l['source'] == col_name and l['target'] == user_details["Fullname"])) for l in links)
        if not link_exists: links.append({"source": user_details["Fullname"], "target": col_name})
    return JsonResponse({"nodes": nodes, "links": links}, safe=False)

@csrf_exempt
def api_announcements(request): return JsonResponse(ANNOUNCEMENTS, safe=False)
@csrf_exempt
def api_messages(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            action = d.get('action')
            if action == 'send':
                new_id = len(MESSAGES) + 1
                msg = { "id": new_id, "sender": d.get("sender"), "receiver": d.get("receiver"), "content": d.get("content"), "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "read": False }
                MESSAGES.insert(0, msg)
                save_json(MESSAGES_FILE, MESSAGES)
                return JsonResponse({"status": "success"})
            elif action == 'list':
                user = d.get("user"); role = d.get("role")
                if role == "admin": return JsonResponse(MESSAGES, safe=False)
                else: return JsonResponse([m for m in MESSAGES if m.get("receiver") == user or m.get("sender") == user], safe=False)
        except Exception as e: return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({}, 405)
@csrf_exempt
def api_change_password(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body); email = d.get('email'); new_pass = d.get('newPassword')
            if email in ACADEMICIANS_BY_EMAIL:
                PASSWORDS_DB[email] = new_pass; save_json(PASSWORDS_FILE, PASSWORDS_DB)
                return JsonResponse({"status": "success"})
        except: return JsonResponse({"error": "Hata"}, 400)
    return JsonResponse({}, 405)

# --- URL YÖNLENDİRMELERİ ---
urlpatterns = [
    # 1. Assets (JS/CSS)
    re_path(r'^assets/(?P<path>.*)$', serve, {'document_root': ASSETS_DIR}),
    
    # 2. Resimler (images klasöründen)
    path('images/<str:image_name>', serve_image),
    path('akademisyen_fotograflari/<str:image_name>', serve_academician_photo),

    # 3. API'ler (Soru işareti sayesinde / olmasa da çalışır)
    re_path(r'^api/login/?$', api_login),
    re_path(r'^api/logout/?$', api_logout),
    re_path(r'^api/admin-data/?$', api_list_admin),
    re_path(r'^api/profile/?$', api_profile),
    re_path(r'^api/decision/?$', api_project_decision),
    re_path(r'^api/top-projects/?$', api_top_projects),
    re_path(r'^api/network-graph/?$', api_network_graph),
    re_path(r'^api/announcements/?$', api_announcements),
    re_path(r'^api/messages/?$', api_messages),
    re_path(r'^api/change-password/?$', api_change_password),
    
    # 4. React (Her şeyi yakalar)
    re_path(r'^(?P<resource>.*)$', serve_react),
]

application = get_wsgi_application()

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
