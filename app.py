import os
import sys
import json
import datetime
import mimetypes
from collections import Counter # EKSİKTİ EKLENDİ
from django.conf import settings
from django.core.management import execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.urls import path, re_path
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

# --- 1. PROJE AYARLARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist') # React Build Klasörü

# MIME Tipleri (Beyaz Ekran Çözümü İçin Kritik)
mimetypes.init()
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("image/svg+xml", ".svg", True)

# Veri Dosyaları Yolları
FILES = {
    'decisions': 'decisions.json', 'logs': 'access_logs.json',
    'announcements': 'announcements.json', 'messages': 'messages.json',
    'passwords': 'passwords.json', 'academicians': 'academicians_merged.json',
    'projects': 'eu_projects_merged_tum.json', 'matches': 'n8n_akademisyen_proje_onerileri.json'
}

# Veri Dosyalarının Tam Yolları
DECISIONS_FILE = os.path.join(BASE_DIR, FILES['decisions'])
LOGS_FILE = os.path.join(BASE_DIR, FILES['logs'])
ANNOUNCEMENTS_FILE = os.path.join(BASE_DIR, FILES['announcements'])
MESSAGES_FILE = os.path.join(BASE_DIR, FILES['messages'])
PASSWORDS_FILE = os.path.join(BASE_DIR, FILES['passwords'])

if not settings.configured:
    settings.configure(
        DEBUG=True, # Hataları görmek için True yaptık
        SECRET_KEY='gizli-anahtar-burada',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'corsheaders',
        ],
        MIDDLEWARE=[
            'corsheaders.middleware.CorsMiddleware', # En üste aldık
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
        ],
        CORS_ALLOW_ALL_ORIGINS=True,
    )

# --- 2. GLOBAL VERİTABANI ---
DB = {'ACADEMICIANS_BY_NAME': {}, 'ACADEMICIANS_BY_EMAIL': {}, 'PROJECTS': {}, 'MATCHES': [], 'FEEDBACK': [], 'LOGS': [], 'ANNOUNCEMENTS': [], 'MESSAGES': [], 'PASSWORDS': {}}

# --- 3. VERİ YÜKLEME ---
def load_data():
    print("--- SİSTEM BAŞLATILIYOR ---")
    
    # JSON Dosyalarını Yükle
    for k, v in FILES.items():
        path = os.path.join(BASE_DIR, v)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if k == 'decisions': DB['FEEDBACK'] = data
                    elif k == 'logs': DB['LOGS'] = data
                    elif k == 'announcements': DB['ANNOUNCEMENTS'] = data
                    elif k == 'messages': DB['MESSAGES'] = data
                    elif k == 'passwords': DB['PASSWORDS'] = data
                    
                    elif k == 'academicians':
                        for p in data:
                            if p.get("Fullname"): DB['ACADEMICIANS_BY_NAME'][p["Fullname"].strip().upper()] = p
                            if p.get("Email"): DB['ACADEMICIANS_BY_EMAIL'][p["Email"].strip().lower()] = p
                            
                    elif k == 'projects':
                        for p in data:
                            pid = str(p.get("project_id", "")).strip()
                            if pid: DB['PROJECTS'][pid] = p
                            
                    elif k == 'matches':
                        raw = [item for sublist in data.values() if isinstance(sublist, list) for item in sublist] if isinstance(data, dict) else data
                        for item in raw:
                            name = item.get('data') or item.get('academician_name')
                            pid = str(item.get('Column3') or item.get('project_id') or "")
                            if name and pid and name != "academician_name":
                                DB['MATCHES'].append({
                                    "name": name.strip(), "projId": pid,
                                    "score": int(item.get('Column7') or item.get('score') or 0),
                                    "reason": item.get('Column6') or item.get('reason') or ""
                                })
            except Exception as e: print(f"Hata ({k}): {e}")

load_data()

# --- 4. YARDIMCI FONKSİYONLAR ---
def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def log_access(name, role, action):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DB['LOGS'].insert(0, {"timestamp": now, "name": name, "role": role, "action": action})
        if len(DB['LOGS']) > 500: DB['LOGS'].pop()
        save_json(LOGS_FILE, DB['LOGS'])
    except: pass

# --- 5. DOSYA SUNUCULARI ---

# React Dosyalarını ve Assets'leri Sunan Fonksiyon (DÜZELTİLDİ)
def serve_react(request, resource=""):
    # Eğer assets veya statik dosya isteniyorsa (css, js, svg vb.)
    if resource and (resource.startswith("assets/") or "." in resource):
        file_path = os.path.join(DIST_DIR, resource)
        if os.path.exists(file_path):
            mtype, _ = mimetypes.guess_type(file_path)
            return FileResponse(open(file_path, 'rb'), content_type=mtype)
    
    # Diğer her şey için index.html döndür (SPA mantığı)
    try:
        return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except FileNotFoundError:
        return HttpResponse(f"Sistem Yükleniyor... (dist klasörü bekleniyor)", status=503)

# Resim Sunucusu
def serve_image(request, image_name):
    try:
        img_path = os.path.join(BASE_DIR, 'images', image_name)
        if os.path.exists(img_path):
            return FileResponse(open(img_path, 'rb'))
        return HttpResponse("Resim yok", status=404)
    except: return HttpResponse("Hata", status=404)

# Akademisyen Fotoğraf Sunucusu
def serve_academician_photo(request, image_name):
    try:
        folder = os.path.join(BASE_DIR, 'akademisyen_fotograflari')
        target_path = os.path.join(folder, image_name)
        
        # 1. Tam eşleşme
        if os.path.exists(target_path):
            return FileResponse(open(target_path, 'rb'))
            
        # 2. Büyük/Küçük harf duyarsız arama
        if os.path.exists(folder):
            target_lower = image_name.lower()
            for f in os.listdir(folder):
                if f.lower() == target_lower:
                    return FileResponse(open(os.path.join(folder, f), 'rb'))
                    
        return HttpResponse("Fotoğraf yok", status=404)
    except: return HttpResponse("Hata", status=404)

# --- 6. API FONKSİYONLARI ---

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            u = d.get('username', '').strip().lower() # Küçük harfe çevir
            p = d.get('password', '').strip()

            if u == "admin" and p == "12345":
                log_access("Admin", "Yönetici", "Giriş Başarılı")
                return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})

            acc = DB['ACADEMICIANS_BY_EMAIL'].get(u)
            if acc:
                stored_pass = DB['PASSWORDS'].get(u)
                default_pass = u.split('@')[0]
                valid_pass = stored_pass if stored_pass else default_pass

                if p == valid_pass:
                    log_access(acc["Fullname"], "Akademisyen", "Giriş Başarılı")
                    return JsonResponse({"status": "success", "role": "academician", "name": acc["Fullname"]})

            log_access(u, "Bilinmiyor", "Hatalı Giriş")
            return JsonResponse({"status": "error", "message": "Hatalı Bilgi"}, status=401)
        except Exception as e: return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({}, status=405)

@csrf_exempt
def api_change_password(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            email = d.get('email')
            DB['PASSWORDS'][email] = d.get('newPassword')
            save_json(PASSWORDS_FILE, DB['PASSWORDS'])
            return JsonResponse({"status": "success"})
        except: return JsonResponse({"status": "error"}, 400)
    return JsonResponse({}, 405)

@csrf_exempt
def api_logout(request): return JsonResponse({"status": "success"})

@csrf_exempt
def api_announcements(request):
    if request.method == 'GET': return JsonResponse(DB['ANNOUNCEMENTS'], safe=False)
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            if d.get("action") == "delete":
                idx = d.get("index")
                if idx is not None and 0 <= idx < len(DB['ANNOUNCEMENTS']):
                    DB['ANNOUNCEMENTS'].pop(idx)
            else:
                DB['ANNOUNCEMENTS'].insert(0, {
                    "id": len(DB['ANNOUNCEMENTS']) + 1,
                    "title": d.get("title"), "content": d.get("content"),
                    "date": datetime.datetime.now().strftime("%d.%m.%Y")
                })
            save_json(ANNOUNCEMENTS_FILE, DB['ANNOUNCEMENTS'])
            return JsonResponse({"status": "success"})
        except: return JsonResponse({"error": "Failed"}, status=400)
    return JsonResponse({}, 405)

def api_list_admin(request):
    stats = {}
    for m in DB['MATCHES']:
        nk = m["name"]
        if nk not in stats:
            det = DB['ACADEMICIANS_BY_NAME'].get(nk.upper(), {})
            
            # Resim Yolu Düzeltme
            img = det.get("Image")
            if img and not img.startswith("http"): img = f"akademisyen_fotograflari/{os.path.basename(img)}"
            
            stats[nk] = {"name": nk, "email": det.get("Email", "-"), "project_count": 0, "best_score": 0, "image": img}
        stats[nk]["project_count"] += 1
        if m["score"] > stats[nk]["best_score"]: stats[nk]["best_score"] = m["score"]
        
    return JsonResponse({
        "academicians": list(stats.values()),
        "feedbacks": DB['FEEDBACK'],
        "logs": DB['LOGS'],
        "announcements": DB['ANNOUNCEMENTS']
    }, safe=False)

@csrf_exempt
def api_profile(request):
    if request.method == 'POST':
        try:
            req_name = json.loads(request.body).get('name')
            raw_profile = DB['ACADEMICIANS_BY_NAME'].get(req_name.upper(), {})

            # Resim Bulma
            img_final = raw_profile.get("Image")
            if img_final and not img_final.startswith("http"):
                img_final = f"/akademisyen_fotograflari/{os.path.basename(img_final)}"
            
            # Eğer JSON'da resim yoksa klasörden bulmaya çalış
            if not img_final:
                 email_user = raw_profile.get("Email", "").split('@')[0].lower()
                 folder = os.path.join(BASE_DIR, 'akademisyen_fotograflari')
                 if os.path.exists(folder):
                     for f in os.listdir(folder):
                         if f.lower().startswith(email_user):
                             img_final = f"/akademisyen_fotograflari/{f}"
                             break

            profile = {
                "Fullname": req_name,
                "Email": raw_profile.get("Email", "-"),
                "Field": raw_profile.get("Field", "-"),
                "Phone": raw_profile.get("Phone", "-"),
                "Image": img_final,
                "Title": raw_profile.get("Title", "Akademisyen"),
                "Duties": raw_profile.get("Duties", [])
            }

            p_matches = [m for m in DB['MATCHES'] if m["name"] == req_name]
            enriched = []
            for m in p_matches:
                pd = DB['PROJECTS'].get(m["projId"], {})
                stat, note, rating = "waiting", "", 0
                for fb in DB['FEEDBACK']:
                    if fb["academician"] == req_name and fb["projId"] == m["projId"]:
                        stat = fb["decision"]; note = fb.get("note", ""); rating = fb.get("rating", 0); break
                
                collabs = []
                for fb in DB['FEEDBACK']:
                    if fb["projId"] == m["projId"] and fb["decision"] == "accepted" and fb["academician"] != req_name:
                        collabs.append(fb["academician"])

                enriched.append({
                    "id": m["projId"], "score": m["score"], "title": pd.get("title") or f"Proje-{m['projId']}",
                    "objective": pd.get("objective", ""), "budget": pd.get("overall_budget", "-"),
                    "status": pd.get("status", "-"), "url": pd.get("url", "#"),
                    "decision": stat, "note": note, "rating": rating, "collaborators": collabs
                })
            enriched.sort(key=lambda x: x['score'], reverse=True)
            return JsonResponse({"profile": profile, "projects": enriched})
        except Exception as e: return JsonResponse({"error": str(e)}, 400)
    return JsonResponse({}, 400)

@csrf_exempt
def api_messages(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            if d.get("action") == "send":
                DB['MESSAGES'].insert(0, {
                    "id": len(DB['MESSAGES'])+1, "sender": d.get("sender"), "receiver": d.get("receiver"),
                    "content": d.get("content"), "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                })
                save_json(MESSAGES_FILE, DB['MESSAGES'])
                return JsonResponse({"status": "success"})
            elif d.get("action") == "list":
                if d.get("role") == "admin": return JsonResponse(DB['MESSAGES'], safe=False)
                u = d.get("user")
                return JsonResponse([m for m in DB['MESSAGES'] if m.get("receiver")==u or m.get("sender")==u], safe=False)
        except: return JsonResponse({}, 400)
    return JsonResponse({}, 405)

@csrf_exempt
def api_project_decision(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            acc, pid = d.get("academician"), d.get("projId")
            found = False
            for item in DB['FEEDBACK']:
                if item["academician"] == acc and item["projId"] == pid:
                    item.update(d)
                    item["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    found = True; break
            if not found:
                d["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                DB['FEEDBACK'].append(d)
            save_json(DECISIONS_FILE, DB['FEEDBACK'])
            return JsonResponse({"status": "success"})
        except: return JsonResponse({"status": "error"}, 400)
    return JsonResponse({}, 405)

def api_network_graph(request):
    user = request.GET.get('user')
    if not user: return JsonResponse({"nodes": [], "links": []})
    
    u_det = DB['ACADEMICIANS_BY_NAME'].get(user.upper(), {})
    img = u_det.get("Image")
    if img and not img.startswith("http"): img = f"akademisyen_fotograflari/{os.path.basename(img)}"
    
    nodes = [{"id": user, "isCenter": True, "img": img}]
    links = []
    collaborators = set()
    
    my_projects = {fb["projId"] for fb in DB['FEEDBACK'] if fb["academician"] == user and fb["decision"] == "accepted"}
    for fb in DB['FEEDBACK']:
        if fb["projId"] in my_projects and fb["academician"] != user and fb["decision"] == "accepted":
            collaborators.add(fb["academician"])
            
    for col in collaborators:
        c_det = DB['ACADEMICIANS_BY_NAME'].get(col.upper(), {})
        c_img = c_det.get("Image")
        if c_img and not c_img.startswith("http"): c_img = f"akademisyen_fotograflari/{os.path.basename(c_img)}"
        
        nodes.append({"id": col, "isCenter": False, "img": c_img})
        links.append({"source": user, "target": col})
        
    return JsonResponse({"nodes": nodes, "links": links}, safe=False)

def api_top_projects(request):
    cnt = Counter(m['projId'] for m in DB['MATCHES']).most_common(50)
    top = []
    for pid, c in cnt:
        pd = DB['PROJECTS'].get(pid, {})
        top.append({"id": pid, "count": c, "title": pd.get("title"), "budget": pd.get("overall_budget"), "status": pd.get("status"), "url": pd.get("url", "#")})
    return JsonResponse(top, safe=False)

# --- 7. URL YÖNLENDİRMELERİ ---
urlpatterns = [
    # API Endpointleri
    path('api/login/', api_login),
    path('api/logout/', api_logout),
    path('api/admin-data/', api_list_admin),
    path('api/profile/', api_profile),
    path('api/decision/', api_project_decision),
    path('api/top-projects/', api_top_projects),
    path('api/network-graph/', api_network_graph),
    path('api/announcements/', api_announcements),
    path('api/messages/', api_messages),
    path('api/change-password/', api_change_password),
    
    # Dosya Sunucuları
    path('images/<str:image_name>', serve_image),
    path('akademisyen_fotograflari/<str:image_name>', serve_academician_photo),
    
    # React Frontend (En sonda olmalı)
    re_path(r'^(?P<resource>.*)$', serve_react),
]

application = get_wsgi_application()

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
