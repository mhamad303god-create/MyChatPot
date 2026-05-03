import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv # استدعاء المكتبة لقراءة الملف المحلي

# بناء المسارات
BASE_DIR = Path(__file__).resolve().parent.parent

# تفعيل قراءة ملف .env من المجلد الرئيسي للمشروع
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = "django-insecure-ptv^zmkxvk(oy$g68p%g177(8=)*-%m3yldpo%jfqs%3=uo7sw"

DEBUG = True

# تم إضافة نطاق Render لضمان العمل عند الرفع
ALLOWED_HOSTS = ['mychatpot.onrender.com', 'localhost', '127.0.0.1', '.onrender.com']

# =========================
# APPS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "chat",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
]

SITE_ID = 1

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # تأكد أنها تحت السكيورتي مباشرة
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "backend.urls"

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =========================
# DATABASE (SQLite محلياً)
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =========================
# STATIC / MEDIA
# =========================
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]

# إعداد WhiteNoise لخدمة الملفات الثابتة في Render
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# GEMINI API (FIX الاحترافي)
# =========================
# سيقرأ من .env محلياً ومن Environment Variables في Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API is configured and ready!")
else:
    print("❌ GEMINI_API_KEY not found! Check your .env file or Render settings.")

# بقية إعدادات ALLAUTH كما هي...