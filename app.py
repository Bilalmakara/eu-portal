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

# 1. AYARLAR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
ASSETS_DIR = os.path.join(DIST_DIR, 'assets')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
PHOTOS_DIR = os.path.join(BASE_DIR, 'akademisyen_fotograflari')

# Dosya Yolları
FILES = {
    'decisions': os.path.join(BASE_DIR, 'decisions.json'),
    'logs': os.path.join(BASE_DIR, 'access_logs.json'),
    'announcements': os.path.join(BASE_DIR, 'announcements.json'),
    'messages': os.path.join(BASE_DIR, 'messages.json'),
    'passwords': os.path.join(BASE_DIR, 'passwords.json'),
    'academicians': os.path.join(BASE_DIR, 'academicians_merged.json'),
    'projects': os.path.join(BASE_DIR, 'eu_projects_merged_tum.json'),
    'matches': os.path.join(BASE_DIR, 'n8n_akademisyen_proje_onerileri.json')
}

# Veri Belleği
DB = {
    'ACADEMICIANS_BY_NAME': {}, 'ACADEMICIANS_BY_EMAIL': {},
    'PROJECTS': {}, 'MATCHES': [], 'FEEDBACK': [],
    'LOGS': [], 'ANNOUNCEMENTS': [], 'MESSAGES': [], 'PASSWORDS': {}
}

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='gizli-anahtar',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=['django.contrib.staticfiles','django.contrib.contenttypes','django.contrib.auth','corsheaders'],
        MIDDLEWARE=['corsheaders.middleware.CorsMiddleware','django.middleware.common.CommonMiddleware'],
        CORS_ALLOW_ALL_ORIGINS=True,
    )

# 2. VERİLERİ YÜKLE
def load_data():
    # JSON Yükleyiciler
    for key, var_name in [('decisions', 'FEEDBACK'), ('logs', 'LOGS'), ('announcements', 'ANNOUNCEMENTS'), 
                          ('messages', 'MESSAGES'), ('passwords', 'PASSWORDS')]:
        if os.path.exists(FILES[key]):
            try:
                with open(FILES[key], 'r', encoding='utf-8') as f: DB[var_name] = json.load(f)
            except: pass

    # Akademisyenler
    if os.path.exists(FILES['academicians']):
        try:
            with open(FILES['academicians'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                for p in data:
                    if p.get("Fullname"): DB['ACADEMICIANS_BY_NAME'][p["Fullname"].strip().upper()] = p
                    if p.get("Email"): DB['ACADEMICIANS_BY_EMAIL'][p["Email"].strip().lower()] = p
        except: pass

    # Projeler
    if os.path.exists(FILES['projects']):
        try:
            with open(FILES['projects'], 'r', encoding='utf-8') as f:
                data = json.load(f)
                for p in data:
                    pid = str(p.get("project_id", "")).strip()
                    if pid: DB['PROJECTS'][pid] = p
        except: pass

    # Eşleşmeler
    if os.path.exists(FILES['matches']):
        try:
            with open(FILES['matches'], 'r', encoding='utf-8') as f:
                raw = json.load(f)
                combined = []
                if isinstance(raw, dict):
                    for v in raw.values():
                        if isinstance(v, list): combined.extend(v)
                elif isinstance(raw, list): combined = raw

                for item in combined:
                    name = item.get('data') or item.get('academician_name')
                    pid = str(item.get('Column3') or item.get('project_id') or "")
                    if name and pid and name != "academician_name":
                        DB['MATCHES'].append({
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
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DB['LOGS'].insert(0, {"timestamp": now, "name": name, "role": role, "action": action})
    if len(DB['LOGS']) > 500: DB['LOGS'].pop()
    save_json(FILES['logs'], DB['LOGS'])

# 4. AKILLI DOSYA SUNUCUSU (Büyük/Küçük Harf Sorununu Çözer)
def serve_files_smart(request, path, folder, default_type=None):
    # 1. Önce tam dosya adını dene
    target_path = os.path.join(folder, path)
    if os.path.exists(target_path):
        mtype, _ = mimetypes.guess_type(target_path)
        return FileResponse(open(target_path, 'rb'), content_type=mtype or default_type)
    
    # 2. Bulamazsa klasördeki tüm dosyaları tara (Case-Insensitive Arama)
    if os.path.exists(folder):
        target_lower = path.lower()
        for filename in os.listdir(folder):
            if filename.lower() == target_lower:
                full_path = os.path.join(folder, filename)
                mtype, _ = mimetypes.guess_type(full_path)
                return FileResponse(open(full_path, 'rb'), content_type=mtype or default_type)
    
    return HttpResponse(status=404)

def serve_react(request, resource=""):
    if resource.startswith("assets/"): return serve_files_smart(request, resource, DIST_DIR)
    if resource and os.path.exists(os.path.join(DIST_DIR, resource)): return serve_files_smart(request, resource, DIST_DIR)
    try: return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except: return HttpResponse("Sistem yükleniyor...", status=503)

# 5. API ENDPOINTLERİ
@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            u = d.get('username', '').strip().lower()
            p = d.get('password', '').strip()
            
            if u == "admin" and p == "12345":
                log_access("Admin", "Yönetici", "Giriş Başarılı")
                return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})
            
            if u in DB['ACADEMICIANS_BY_EMAIL']:
                real_pass = DB['PASSWORDS'].get(u, u.split('@')[0])
                if p == real_pass:
                    acc = DB['ACADEMICIANS_BY_EMAIL'][u]
                    log_access(acc["Fullname"], "Akademisyen", "Giriş Başarılı")
                    return JsonResponse({"status": "success", "role": "academician", "name": acc["Fullname"]})
            
            return JsonResponse({"status": "error", "message": "Giriş başarısız"}, status=401)
        except Exception as e: return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({}, status=405)

@csrf_exempt
def api_profile(request):
    if request.method == 'POST':
        try:
            req_name = json.loads(request.body).get('name')
            if not req_name: return JsonResponse({}, 400)
            
            raw_profile = DB['ACADEMICIANS_BY_NAME'].get(req_name.upper(), {})
            
            # Fotoğraf yolu düzeltme
            img_path = raw_profile.get("Image")
            if img_path and not img_path.startswith("http"):
                img_path = f"/akademisyen_fotograflari/{os.path.basename(img_path)}"

            profile = {
                "Fullname": req_name, "Email": raw_profile.get("Email", "-"), 
                "Field": raw_profile.get("Field", "-"), "Phone": raw_profile.get("Phone", "-"), 
                "Image": img_path, "Duties": raw_profile.get("Duties", [])
            }

            p_matches = [m for m in DB['MATCHES'] if m["name"] == req_name]
            enriched = []
            for m in p_matches:
                pd = DB['PROJECTS'].get(m["projId"], {})
                stat, note, rating = "waiting", "", 0
                for fb in DB['FEEDBACK']:
                    if fb["academician"] == req_name and fb["projId"] == m["projId"]:
                        stat = fb["decision"]; note = fb.get("note", ""); rating = fb.get("rating", 0); break
                
                collaborators = []
                for fb in DB['FEEDBACK']:
                    if fb["projId"] == m["projId"] and fb["decision"] == "accepted" and fb["academician"] != req_name:
                        collaborators.append(fb["academician"])
                
                project_title = pd.get("title") or pd.get("acronym") or f"Proje-{m['projId']}"
                enriched.append({
                    "id": m["projId"], "score": m["score"], "reason": m["reason"], "title": project_title,
                    "objective": pd.get("objective", ""), "budget": pd.get("overall_budget", "-"), 
                    "status": pd.get("status", "-"), "url": pd.get("url", "#"), 
                    "decision": stat, "note": note, "rating": rating, "collaborators": collaborators
                })
            
            enriched.sort(key=lambda x: x['score'], reverse=True)
            return JsonResponse({"profile": profile, "projects": enriched})
        except Exception as e: return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({}, 400)

@csrf_exempt
def api_project_decision(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            acc = d.get("academician"); pid = d.get("projId"); dec = d.get("decision")
            found = False
            for item in DB['FEEDBACK']:
                if item["academician"] == acc and item["projId"] == pid:
                    item.update({"decision": dec, "note": d.get("note", ""), "rating": int(d.get("rating", 0)), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
                    found = True; break
            if not found:
                DB['FEEDBACK'].append({"academician": acc, "projId": pid, "projectTitle": d.get("projectTitle"), "decision": dec, "note": d.get("note", ""), "rating": int(d.get("rating", 0)), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_json(FILES['decisions'], DB['FEEDBACK'])
            return JsonResponse({"status": "success"})
        except Exception as e: return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({}, 405)

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
    
    return JsonResponse({
        "academicians": list(stats.values()), 
        "feedbacks": DB['FEEDBACK'], 
        "logs": DB['LOGS'], 
        "announcements": DB['ANNOUNCEMENTS']
    }, safe=False)

def api_top_projects(request):
    cnt = Counter(m['projId'] for m in DB['MATCHES']).most_common(50)
    top = []
    for pid, c in cnt:
        pd = DB['PROJECTS'].get(pid, {})
        top.append({
            "id": pid, "count": c, "title": pd.get("title") or f"Proje-{pid}",
            "budget": pd.get("overall_budget", "-"), "status": pd.get("status", "-"), "url": pd.get("url", "#")
        })
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
        if fb["projId"] in my_projects and fb["academician"] != user and fb["decision"] == "accepted":
            collaborators.add(fb["academician"])
            
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
        if d.get("action") == "delete":
            DB['ANNOUNCEMENTS'].pop(d.get("index"))
        else:
            DB['ANNOUNCEMENTS'].insert(0, {"title": d.get("title"), "content": d.get("content"), "date": datetime.datetime.now().strftime("%d.%m.%Y")})
        save_json(FILES['announcements'], DB['ANNOUNCEMENTS'])
        return JsonResponse({"status": "success"})
    return JsonResponse(DB['ANNOUNCEMENTS'], safe=False)

@csrf_exempt
def api_messages(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        if d.get("action") == "send":
            msg = {"id": len(DB['MESSAGES'])+1, "sender": d.get("sender"), "receiver": d.get("receiver"), "content": d.get("content"), "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
            DB['MESSAGES'].insert(0, msg)
            save_json(FILES['messages'], DB['MESSAGES'])
            return JsonResponse({"status": "success"})
        elif d.get("action") == "list":
            if d.get("role") == "admin": return JsonResponse(DB['MESSAGES'], safe=False)
            u = d.get("user")
            return JsonResponse([m for m in DB['MESSAGES'] if m["sender"]==u or m["receiver"]==u], safe=False)
    return JsonResponse([], safe=False)

@csrf_exempt
def api_change_password(request):
    if request.method == 'POST':
        d = json.loads(request.body)
        DB['PASSWORDS'][d.get('email')] = d.get('newPassword')
        save_json(FILES['passwords'], DB['PASSWORDS'])
        return JsonResponse({"status": "success"})
    return JsonResponse({}, 400)

@csrf_exempt
def api_logout(request): return JsonResponse({"status": "success"})

# URL YÖNLENDİRMELERİ
urlpatterns = [
    # Akıllı Resim Sunucusu (Klasördeki dosyayı adını büyüklü/küçüklü arar)
    re_path(r'^images/(?P<path>.*)$', lambda r, path: serve_files_smart(r, path, IMAGES_DIR, "image/png")),
    re_path(r'^akademisyen_fotograflari/(?P<path>.*)$', lambda r, path: serve_files_smart(r, path, PHOTOS_DIR, "image/jpeg")),
    
    # API
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
    
    # React
    re_path(r'^(?P<resource>.*)$', serve_react),
]

application = get_wsgi_application()

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
