import os
import sys
import json
import datetime
import mimetypes
from django.conf import settings
from django.core.management import execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.urls import path, re_path
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

# 1. TEMEL AYARLAR
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
        CORS_ALLOW_CREDENTIALS=True,
    )

# 2. VERİLERİ YÜKLE
def load_data():
    print("--- VERİLER YÜKLENİYOR ---")
    # Basit JSON'lar
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
                for p in json.load(f):
                    if p.get("Fullname"): DB['ACADEMICIANS_BY_NAME'][p["Fullname"].strip().upper()] = p
                    if p.get("Email"): DB['ACADEMICIANS_BY_EMAIL'][p["Email"].strip().lower()] = p
    
    # Projeler
    if os.path.exists(FILES['projects']):
        try:
            with open(FILES['projects'], 'r', encoding='utf-8') as f:
                for p in json.load(f):
                    pid = str(p.get("project_id", "")).strip()
                    if pid: DB['PROJECTS'][pid] = p
        except: pass

load_data() # Başlangıçta çalıştır

def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def log_access(name, role, action):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DB['LOGS'].insert(0, {"timestamp": now, "name": name, "role": role, "action": action})
    if len(DB['LOGS']) > 500: DB['LOGS'].pop()
    save_json(FILES['logs'], DB['LOGS'])

# 3. ÖZEL DOSYA SUNUCULARI (RESİMLER BURADAN GEÇECEK)

def serve_assets(request, path):
    # React JS ve CSS dosyaları için
    file_path = os.path.join(ASSETS_DIR, path)
    if os.path.exists(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if path.endswith(".js"): mime_type = "application/javascript"
        elif path.endswith(".css"): mime_type = "text/css"
        return FileResponse(open(file_path, 'rb'), content_type=mime_type)
    return HttpResponse(status=404)

def serve_logo_images(request, image_name):
    # 'images' klasöründeki dosyalar (LOGO BURADA - .png)
    file_path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(file_path):
        # Logolar genelde PNG'dir ama garanti olsun
        return FileResponse(open(file_path, 'rb'), content_type="image/png")
    return HttpResponse("Logo bulunamadı", status=404)

def serve_academician_photos(request, image_name):
    # 'akademisyen_fotograflari' klasörü (FOTOĞRAFLAR BURADA - .jpg)
    file_path = os.path.join(PHOTOS_DIR, image_name)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), content_type="image/jpeg")
    return HttpResponse("Fotoğraf bulunamadı", status=404)

def serve_react_app(request, resource=""):
    # Diğer her şey için index.html (Sayfa yenileyince 404 vermesin diye)
    try:
        return FileResponse(open(os.path.join(DIST_DIR, 'index.html'), 'rb'))
    except FileNotFoundError:
        return HttpResponse("Sistem yükleniyor... (Build bekleniyor)", status=503)

# 4. API (GİRİŞ İŞLEMLERİ)

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            d = json.loads(request.body)
            u = d.get('username', '').strip()
            p = d.get('password', '').strip()
            print(f"LOGIN DENEMESİ: '{u}' şifre: '{p}'") # Render Loglarında görebilirsin

            # Admin Girişi
            if u == "admin" and p == "12345":
                log_access("Admin", "Yönetici", "Giriş Başarılı")
                return JsonResponse({"status": "success", "role": "admin", "name": "Yönetici"})
            
            # Akademisyen Girişi
            acc = DB['ACADEMICIANS_BY_EMAIL'].get(u.lower())
            if acc:
                stored = DB['PASSWORDS'].get(u.lower())
                real_pass = stored if stored else u.lower().split('@')[0]
                if p == real_pass:
                    log_access(acc["Fullname"], "Akademisyen", "Giriş Başarılı")
                    return JsonResponse({"status": "success", "role": "academician", "name": acc["Fullname"]})
            
            return JsonResponse({"status": "error", "message": "Hatalı Giriş"}, status=401)
        except Exception as e:
            print(f"LOGIN HATASI: {e}")
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({}, status=405)

# Diğer API'ler (Boş ama çalışır durumda)
@csrf_exempt
def api_logout(request): return JsonResponse({"status": "success"})
@csrf_exempt
def api_announcements(request): return JsonResponse(DB['ANNOUNCEMENTS'], safe=False)
@csrf_exempt
def api_messages(request): return JsonResponse(DB['MESSAGES'], safe=False)
@csrf_exempt
def api_list_admin(request): return JsonResponse({"academicians": [], "feedbacks": DB['FEEDBACK'], "logs": DB['LOGS'], "announcements": DB['ANNOUNCEMENTS']}, safe=False)
@csrf_exempt
def api_profile(request):
    if request.method == 'POST':
        req_name = json.loads(request.body).get('name')
        raw = DB['ACADEMICIANS_BY_NAME'].get(req_name.upper(), {})
        return JsonResponse({"profile": raw, "projects": []}) 
    return JsonResponse({}, 400)
@csrf_exempt
def api_change_password(request):
    try:
        d = json.loads(request.body); email = d.get('email'); new_pass = d.get('newPassword')
        if email in DB['ACADEMICIANS_BY_EMAIL']: DB['PASSWORDS'][email] = new_pass; save_json(FILES['passwords'], DB['PASSWORDS']); return JsonResponse({"status": "success"})
    except: return JsonResponse({"error": "Hata"}, 400)


# 5. URL YÖNLENDİRMELERİ (EN ÖNEMLİ KISIM)
urlpatterns = [
    # A. Dosyalar (React bunlara direkt erişir)
    re_path(r'^assets/(?P<path>.*)$', serve_assets),
    re_path(r'^images/(?P<image_name>.*)$', serve_logo_images),
    re_path(r'^akademisyen_fotograflari/(?P<image_name>.*)$', serve_academician_photos),

    # B. API (Sonunda slash olsa da olmasa da kabul et: ? işareti)
    re_path(r'^api/login/?$', api_login),
    re_path(r'^api/logout/?$', api_logout),
    re_path(r'^api/admin-data/?$', api_list_admin),
    re_path(r'^api/profile/?$', api_profile),
    re_path(r'^api/announcements/?$', api_announcements),
    re_path(r'^api/messages/?$', api_messages),
    re_path(r'^api/change-password/?$', api_change_password),

    # C. React Uygulaması (Geri kalan her şey buraya)
    re_path(r'^.*$', serve_react_app),
]

application = get_wsgi_application()

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
