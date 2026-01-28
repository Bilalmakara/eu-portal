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

# --- 1. AYARLAR ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
# Akademisyen fotoğrafları klasörü
PHOTOS_DIR = os.path.join(BASE_DIR, 'akademisyen_fotograflari')

FILES = {
    'decisions': 'decisions.json', 'logs': 'access_logs.json',
    'announcements': 'announcements.json', 'messages': 'messages.json',
    'passwords': 'passwords.json', 'academicians': 'academicians_merged.json',
    'projects': 'eu_projects_merged_tum.json', 'matches': 'n8n_akademisyen_proje_onerileri.json'
}

DB = {'ACADEMICIANS_BY_NAME': {}, 'ACADEMICIANS_BY_EMAIL': {}, 'PROJECTS': {}, 'MATCHES': [], 'FEEDBACK': [], 'LOGS': [], 'ANNOUNCEMENTS': [], 'MESSAGES': [], 'PASSWORDS': {}}

if not settings.configured:
    settings.configure(
        DEBUG=True, SECRET_KEY='gizli', ROOT_URLCONF=__name__, ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=['django.contrib.staticfiles','django.contrib.contenttypes','django.contrib.auth','corsheaders'],
        MIDDLEWARE=['corsheaders.middleware.CorsMiddleware','django.middleware.common.CommonMiddleware'],
        CORS_ALLOW_ALL_ORIGINS=True,
    )

# --- 2. VERİ YÜKLEME ---
def load_data():
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
            except: pass
load_data()

# --- 3. AKILLI DOSYA BULUCU (HEM İSİM HEM YOL DÜZELTİR) ---
def serve_smart_file(request, path, folder):
    # 1. Klasör var mı kontrol et
    if not os.path.exists(folder):
        return HttpResponse(f"KLASOR YOK: {folder}", status=404)

    # 2. İstenen dosya ismini (yoldan temizle) al. Örn: "klasor/Ahmet.jpg" -> "Ahmet.jpg"
    filename = os.path.basename(path)
    
    # 3. Klasördeki dosyaları listele ve eşleşme ara (Büyük/Küçük harf duyarsız)
    try:
        all_files = os.listdir(folder)
    except:
        return HttpResponse("Klasör okunamadı", status=500)

    # Tam eşleşme veya küçük harf eşleşmesi ara
    found_file = None
    for f in all_files:
        if f.lower() == filename.lower():
            found_file = f
            break
    
    if found_file:
        full_path = os.path.join(folder, found_file)
        mtype, _ = mimetypes.guess_type(full_path)
        return FileResponse(open(full_path, 'rb'), content_type=mtype or "application/octet-stream")

    return HttpResponse(f"DOSYA YOK: {filename} (Klasörde {len(all_files)} dosya var)", status=404)

# --- 4. DEBUG ENDPOINT (DOSYALARI LİSTELE) ---
def check_files_view(request):
    report = {
        "DURUM": "Aktif",
        "KLASORLER": {
            "PHOTOS_DIR": PHOTOS_DIR,
            "IMAGES_DIR": IMAGES_DIR
        },
        "DOSYA_LISTESI": {}
    }
    
    # Fotoğraflar klasöründeki ilk 20 dosya
    if os.path.exists(PHOTOS_DIR):
        files = os.listdir(PHOTOS_DIR)
        report["DOSYA_LISTESI"]["akademisyen_fotograflari"] = {
            "toplam_sayi": len(files),
            "ornekler": files[:20] # İlk 20 tanesini göster
        }
    else:
        report["DOSYA_LISTESI"]["akademisyen_fotograflari"] = "KLASÖR BULUNAMADI!"

    # Images klasörü
    if os.path.exists(IMAGES_DIR):
        report["DOSYA_LISTESI"]["images"] = os.listdir(IMAGES_DIR)
    else:
        report["DOSYA_LISTESI"]["images"] = "KLASÖR BULUNAMADI!"

    return JsonResponse(report, json_dumps_params={'indent': 4})

# --- 5. API'LER ---
@csrf_exempt
def api_login(request):
    try:
        d = json.loads(request.body)
        u, p = d.get('username', '').strip().lower(), d.get('password', '').strip()
        if u == "admin" and p == "12345": return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})
        if u in DB['ACADEMICIANS_BY_EMAIL']:
            real = DB['PASSWORDS'].get(u, u.split('@')[0])
            if p == real:
                acc = DB['ACADEMICIANS_BY_EMAIL'][u]
                return JsonResponse({"status": "success", "role": "academician", "name": acc.get("Fullname")})
        return JsonResponse({"status": "error", "message": "Hatalı Giriş"}, status=401)
    except: return JsonResponse({}, 400)

@csrf_exempt
def api_profile(request):
    try:
        name = json.loads(request.body).get('name')
        raw = DB['ACADEMICIANS_BY_NAME'].get(name.upper(), {})
        
        # RESİM YOLU DÜZELTME (Sadece dosya ismini alıyoruz)
        img_raw = raw.get("Image", "")
        img_final = None
        if img_raw:
            if img_raw.startswith("http"): img_final = img_raw
            else:
                # Veritabanında "akademisyen_fotograflari/Ahmet.jpg" yazsa bile
                # biz sadece "Ahmet.jpg" kısmını alıp kendi yolumuzu ekliyoruz.
                filename = os.path.basename(img_raw)
                img_final = f"/akademisyen_fotograflari/{filename}"

        # Projeleri filtrele
        matches = [m for m in DB['MATCHES'] if m["name"] == name]
        projects = []
        for m in matches:
            pd = DB['PROJECTS'].get(m["projId"], {})
            stat = "waiting" # Basitleştirildi
            projects.append({
                "id": m["projId"], "title": pd.get("title") or f"Proje-{m['projId']}", 
                "score": m["score"], "status": pd.get("status", "-"), 
                "budget": pd.get("overall_budget", "-"), "decision": stat, "url": pd.get("url", "#")
            })
        projects.sort(key=lambda x: x['score'], reverse=True)
        
        return JsonResponse({
            "profile": {
                "Fullname": name, "Email": raw.get("Email"), "Phone": raw.get("Phone"), 
                "Title": raw.get("Title", "Akademisyen"), "Image": img_final, 
                "Duties": raw.get("Duties", [])
            },
            "projects": projects
        })
    except Exception as e: return JsonResponse({"error": str(e)}, 500)

# Diğer API placeholderları
def api_dummy(r): return JsonResponse({})
def serve_react(r, resource=""):
    try: return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except: return HttpResponse("Yükleniyor...", status=503)

urlpatterns = [
    # KONTROL SAYFASI
    path('check-files/', check_files_view),
    
    # DOSYALAR (Regex ile her şeyi yakala)
    re_path(r'^images/(?P<path>.*)$', lambda r, path: serve_smart_file(r, path, IMAGES_DIR)),
    re_path(r'^akademisyen_fotograflari/(?P<path>.*)$', lambda r, path: serve_smart_file(r, path, PHOTOS_DIR)),
    
    # API
    re_path(r'^api/login/?$', api_login),
    re_path(r'^api/profile/?$', api_profile),
    re_path(r'^api/.*$', api_dummy),
    
    # REACT
    re_path(r'^(?P<resource>.*)$', serve_react),
]

application = get_wsgi_application()
if __name__ == "__main__": execute_from_command_line(sys.argv)
