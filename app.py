import os
import sys
import json
import datetime
import mimetypes
from collections import Counter
from django.conf import settings
from django.core.management import execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.urls import re_path
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

# --- 1. AYARLAR ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
PHOTOS_DIR = os.path.join(BASE_DIR, 'akademisyen_fotograflari')

# MIME Tipleri (Beyaz Ekran Sorunu İçin Kritik)
mimetypes.init()
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("image/svg+xml", ".svg", True)

FILES = {
    'decisions': 'decisions.json', 'logs': 'access_logs.json',
    'announcements': 'announcements.json', 'messages': 'messages.json',
    'passwords': 'passwords.json', 'academicians': 'academicians_merged.json',
    'projects': 'eu_projects_merged_tum.json', 'matches': 'n8n_akademisyen_proje_onerileri.json'
}

DB = {'ACADEMICIANS_BY_NAME': {}, 'ACADEMICIANS_BY_EMAIL': {}, 'PROJECTS': {}, 'MATCHES': [], 'FEEDBACK': [], 'LOGS': [], 'ANNOUNCEMENTS': [], 'MESSAGES': [], 'PASSWORDS': {}}

if not settings.configured:
    settings.configure(
        DEBUG=True, SECRET_KEY='gizli-anahtar-super-guvenli', ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=['django.contrib.staticfiles','django.contrib.contenttypes','django.contrib.auth','corsheaders'],
        MIDDLEWARE=['corsheaders.middleware.CorsMiddleware','django.middleware.common.CommonMiddleware'],
        CORS_ALLOW_ALL_ORIGINS=True,
    )

# --- 2. VERİ YÜKLEME ---
def load_data():
    print("--- VERİLER YÜKLENİYOR ---")
    for k, v in FILES.items():
        path = os.path.join(BASE_DIR, v)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if k == 'academicians':
                        for p in data:
                            if p.get("Fullname"): DB['ACADEMICIANS_BY_NAME'][p["Fullname"].strip().upper()] = p
                            if p.get("Email"): DB['ACADEMICIANS_BY_EMAIL'][p["Email"].strip().lower()] = p
                    elif k == 'projects':
                        for p in data: DB['PROJECTS'][str(p.get("project_id", "")).strip()] = p
                    elif k == 'matches':
                        raw = [item for sublist in data.values() if isinstance(sublist, list) for item in sublist] if isinstance(data, dict) else data
                        for item in raw:
                            name = item.get('data') or item.get('academician_name')
                            pid = str(item.get('Column3') or item.get('project_id') or "")
                            if name and pid and name != "academician_name":
                                DB['MATCHES'].append({"name": name.strip(), "projId": pid, "score": int(item.get('Column7') or item.get('score') or 0)})
                    elif k == 'decisions': DB['FEEDBACK'] = data
                    elif k == 'announcements': DB['ANNOUNCEMENTS'] = data
                    elif k == 'messages': DB['MESSAGES'] = data
                    elif k == 'passwords': DB['PASSWORDS'] = data
            except Exception as e: print(f"HATA ({k}): {e}")
load_data()

# --- 3. YARDIMCI FONKSİYONLAR ---
def save_json(key, data):
    try:
        with open(os.path.join(BASE_DIR, FILES[key]), 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def log_access(name, role, action):
    DB['LOGS'].insert(0, {"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "name": name, "role": role, "action": action})
    save_json('logs', DB['LOGS'])

# --- 4. AKILLI DOSYA SUNUCUSU (RESİMLER İÇİN) ---
def serve_smart_file(request, path, folder):
    # 1. Dosya yolu temizliği
    clean_path = path.lstrip('/')
    
    # 2. Tam eşleşme ara
    full_path = os.path.join(folder, clean_path)
    if os.path.exists(full_path):
        mtype, _ = mimetypes.guess_type(full_path)
        return FileResponse(open(full_path, 'rb'), content_type=mtype)

    # 3. Bulamazsa klasördeki dosya isimlerini tara (Büyük/Küçük harf duyarsız)
    # Örn: 'aayildirim.jpg' istenir ama sistemde 'AAYILDIRIM.JPG' varsa bulur.
    filename = os.path.basename(clean_path).lower()
    if os.path.exists(folder):
        for f in os.listdir(folder):
            if f.lower() == filename:
                real_path = os.path.join(folder, f)
                mtype, _ = mimetypes.guess_type(real_path)
                return FileResponse(open(real_path, 'rb'), content_type=mtype)
    
    return HttpResponse(status=404)

# --- 5. REACT SUNUCUSU (BEYAZ EKRAN ÇÖZÜMÜ) ---
def serve_react(request, resource=""):
    # Eğer kaynak isteniyorsa (css, js, png vb.) ve dosya varsa gönder
    if resource:
        path = os.path.join(DIST_DIR, resource)
        if os.path.exists(path):
            mtype, _ = mimetypes.guess_type(path)
            return FileResponse(open(path, 'rb'), content_type=mtype)
    
    # Diğer tüm durumlarda (sayfa yenileme vb.) index.html gönder
    try:
        return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except FileNotFoundError:
        return HttpResponse("Sistem yükleniyor... (Lütfen 1 dakika sonra yenileyin)", status=503)

# --- 6. API ENDPOINTLERİ ---
@csrf_exempt
def api_login(request):
    try:
        d = json.loads(request.body)
        u, p = d.get('username', '').strip().lower(), d.get('password', '').strip()
        
        if u == "admin" and p == "12345":
            log_access("Admin", "Yönetici", "Giriş Başarılı")
            return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})
        
        if u in DB['ACADEMICIANS_BY_EMAIL']:
            real = DB['PASSWORDS'].get(u, u.split('@')[0])
            if p == real:
                acc = DB['ACADEMICIANS_BY_EMAIL'][u]
                log_access(acc.get("Fullname"), "Akademisyen", "Giriş Başarılı")
                return JsonResponse({"status": "success", "role": "academician", "name": acc.get("Fullname")})
        
        return JsonResponse({"status": "error", "message": "Hatalı Kullanıcı Adı veya Şifre"}, status=401)
    except Exception as e: return JsonResponse({"error": str(e)}, 400)

@csrf_exempt
def api_profile(request):
    try:
        name = json.loads(request.body).get('name')
        raw = DB['ACADEMICIANS_BY_NAME'].get(name.upper(), {})
        
        # Fotoğraf yolu oluşturma 
        img_raw = raw.get("Image", "")
        img_final = None
        if img_raw:
            if img_raw.startswith("http"): img_final = img_raw
            else:
                # Sadece dosya ismini al, klasörü biz ekleriz
                filename = os.path.basename(img_raw)
                img_final = f"/akademisyen_fotograflari/{filename}"

        # Projeleri Bul
        my_matches = [m for m in DB['MATCHES'] if m["name"] == name]
        projects = []
        for m in my_matches:
            pd = DB['PROJECTS'].get(m["projId"], {})
            stat = "waiting"
            note = ""
            rating = 0
            for fb in DB['FEEDBACK']:
                if fb["academician"] == name and fb["projId"] == m["projId"]:
                    stat = fb["decision"]; note = fb.get("note", ""); rating = fb.get("rating", 0); break
            
            collabs = []
            for fb in DB['FEEDBACK']:
                if fb["projId"] == m["projId"] and fb["decision"] == "accepted" and fb["academician"] != name:
                    collabs.append(fb["academician"])

            projects.append({
                "id": m["projId"], 
                "title": pd.get("title") or f"Proje-{m['projId']}", 
                "score": m["score"], 
                "status": pd.get("status", "-"), 
                "budget": pd.get("overall_budget", "-"), 
                "objective": pd.get("objective", ""),
                "decision": stat, 
                "note": note,
                "rating": rating,
                "collaborators": collabs,
                "url": pd.get("url", "#")
            })
        
        projects.sort(key=lambda x: x['score'], reverse=True)
        
        return JsonResponse({
            "profile": {
                "Fullname": name, "Email": raw.get("Email"), "Phone": raw.get("Phone"), 
                "Title": raw.get("Title", "Akademisyen"), "Image": img_final, 
                "Field": raw.get("Field", "-"),
                "Duties": raw.get("Duties", [])
            },
            "projects": projects
        })
    except Exception as e: return JsonResponse({"error": str(e)}, 500)

@csrf_exempt
def api_project_decision(request):
    try:
        d = json.loads(request.body)
        acc, pid, dec = d.get("academician"), d.get("projId"), d.get("decision")
        found = False
        for item in DB['FEEDBACK']:
            if item["academician"] == acc and item["projId"] == pid:
                item.update({"decision": dec, "note": d.get("note", ""), "rating": int(d.get("rating", 0)), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
                found = True; break
        if not found:
            DB['FEEDBACK'].append({"academician": acc, "projId": pid, "projectTitle": d.get("projectTitle"), "decision": dec, "note": d.get("note", ""), "rating": int(d.get("rating", 0)), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_json('decisions', DB['FEEDBACK'])
        return JsonResponse({"status": "success"})
    except: return JsonResponse({"status": "error"}, 400)

# Admin ve Diğer API'ler
def api_list_admin(request):
    stats = {}
    for m in DB['MATCHES']:
        nk = m["name"]
        if nk not in stats:
            det = DB['ACADEMICIANS_BY_NAME'].get(nk.upper(), {})
            img = det.get("Image")
            if img and not img.startswith("http"): img = f"akademisyen_fotograflari/{os.path.basename(img)}"
            stats[nk] = {"name": nk, "email": det.get("Email", "-"), "project_count": 0, "best_score": 0, "image": img}
        stats[nk]["project_count"] += 1
        if m["score"] > stats[nk]["best_score"]: stats[nk]["best_score"] = m["score"]
    return JsonResponse({"academicians": list(stats.values()), "feedbacks": DB['FEEDBACK'], "logs": DB['LOGS'], "announcements": DB['ANNOUNCEMENTS']}, safe=False)

def api_top_projects(request):
    cnt = Counter(m['projId'] for m in DB['MATCHES']).most_common(50)
    top = []
    for pid, c in cnt:
        pd = DB['PROJECTS'].get(pid, {})
        top.append({"id": pid, "count": c, "title": pd.get("title") or f"Proje-{pid}", "budget": pd.get("overall_budget", "-"), "status": pd.get("status", "-"), "url": pd.get("url", "#")})
    return JsonResponse(top, safe=False)

def api_network_graph(request):
    user = request.GET.get('user')
    if not user: return JsonResponse({"nodes": [], "links": []})
    u_det = DB['ACADEMICIANS_BY_NAME'].get(user.upper(), {})
    u_img = u_det.get("Image")
    if u_img and not u_img.startswith("http"): u_img = f"akademisyen_fotograflari/{os.path.basename(u_img)}"
    nodes = [{"id": user, "isCenter": True, "img": u_img}]
    links = []
    collaborators = set()
    my_projects = {fb["projId"] for fb in DB['FEEDBACK'] if fb["academician"] == user and fb["decision"] == "accepted"}
    for fb in DB['FEEDBACK']:
        if fb["projId"] in my_projects and fb["academician"] != user and fb["decision"] == "accepted": collaborators.add(fb["academician"])
    for col in collaborators:
        c_det = DB['ACADEMICIANS_BY_NAME'].get(col.upper(), {})
        c_img = c_det.get("Image")
        if c_img and not c_img.startswith("http"): c_img = f"akademisyen_fotograflari/{os.path.basename(c_img)}"
        nodes.append({"id": col, "isCenter": False, "img": c_img})
        links.append({"source": user, "target": col})
    return JsonResponse({"nodes": nodes, "links": links}, safe=False)

@csrf_exempt
def api_announcements(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        if d.get("action") == "delete": DB['ANNOUNCEMENTS'].pop(d.get("index"))
        else: DB['ANNOUNCEMENTS'].insert(0, {"title": d.get("title"), "content": d.get("content"), "date": datetime.datetime.now().strftime("%d.%m.%Y")})
        save_json('announcements', DB['ANNOUNCEMENTS'])
        return JsonResponse({"status": "success"})
    return JsonResponse(DB['ANNOUNCEMENTS'], safe=False)

@csrf_exempt
def api_messages(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        if d.get("action") == "send":
            DB['MESSAGES'].insert(0, {"id": len(DB['MESSAGES'])+1, "sender": d.get("sender"), "receiver": d.get("receiver"), "content": d.get("content"), "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")})
            save_json('messages', DB['MESSAGES'])
            return JsonResponse({"status": "success"})
        elif d.get("action") == "list":
            if d.get("role") == "admin": return JsonResponse(DB['MESSAGES'], safe=False)
            return JsonResponse([m for m in DB['MESSAGES'] if m["sender"]==d.get("user") or m["receiver"]==d.get("user")], safe=False)
    return JsonResponse([], safe=False)

@csrf_exempt
def api_change_password(request):
    try:
        d = json.loads(request.body)
        DB['PASSWORDS'][d.get('email')] = d.get('newPassword')
        save_json('passwords', DB['PASSWORDS'])
        return JsonResponse({"status": "success"})
    except: return JsonResponse({}, 400)

@csrf_exempt
def api_logout(request): return JsonResponse({"status": "success"})

# --- 7. URL YÖNLENDİRMELERİ ---
urlpatterns = [
    # Fotoğraflar ve Resimler (Akıllı Arama)
    re_path(r'^images/(?P<path>.*)$', lambda r, path: serve_smart_file(r, path, IMAGES_DIR)),
    re_path(r'^akademisyen_fotograflari/(?P<path>.*)$', lambda r, path: serve_smart_file(r, path, PHOTOS_DIR)),
    
    # API
    re_path(r'^api/login/?$', api_login),
    re_path(r'^api/logout/?$', api_logout),
    re_path(r'^api/profile/?$', api_profile),
    re_path(r'^api/decision/?$', api_project_decision),
    re_path(r'^api/admin-data/?$', api_list_admin),
    re_path(r'^api/top-projects/?$', api_top_projects),
    re_path(r'^api/network-graph/?$', api_network_graph),
    re_path(r'^api/announcements/?$', api_announcements),
    re_path(r'^api/messages/?$', api_messages),
    re_path(r'^api/change-password/?$', api_change_password),
    
    # React (Catch-all en sonda)
    re_path(r'^(?P<resource>.*)$', serve_react),
]

application = get_wsgi_application()

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
