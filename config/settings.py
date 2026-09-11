"""M2 所需的最小 Django 配置。产品默认 locale 为 zh-CN。"""
from pathlib import Path

BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY='development-only-not-for-production'
DEBUG=True
ALLOWED_HOSTS=[]
ROOT_URLCONF='config.urls'
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','accounts','competitions','materials','projects','modeling','analysis']
MIDDLEWARE=['django.contrib.sessions.middleware.SessionMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','accounts.middleware.ForcedPasswordChangeMiddleware']
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
LANGUAGE_CODE='zh-hans'
USE_I18N=True
USE_TZ=True
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
STATIC_URL='static/'
LOGIN_URL='/accounts/login/'
AUTH_USER_MODEL='accounts.User'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
