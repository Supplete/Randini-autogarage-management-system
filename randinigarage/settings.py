
# Import required Python modules
from pathlib import Path  # Path manipulation for file system operations
from decouple import config  # Environment variable management
import os  # Operating system interface

# Install PyMySQL as MySQLdb
import pymysql
pymysql.install_as_MySQLdb()

# ─────────────────────────────────────────────────────────────
# CORE DJANGO SETTINGS
# ─────────────────────────────────────────────────────────────

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR points to the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Generate new key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
# Secret key is loaded from environment variables for security
SECRET_KEY = config('SECRET_KEY', default='django-insecure-kus*1)3k$i=@u%^=+la69fkn!lw*@l!&x2g(wx5zz^65w7%e&_')

# SECURITY WARNING: don't run with debug turned on in production!
# Set to False in production for security and performance
# Debug mode exposes sensitive information and reduces performance
DEBUG = config('DEBUG', default=True, cast=bool)

# Allowed hosts for the application
# In production, add your domain: 'yourdomain.com,www.yourdomain.com'
# This prevents Host header attacks and ensures requests only from allowed domains
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver', cast=lambda v: [s.strip() for s in v.split(',')])

# CSRF Trusted Origins for proxy and development servers
# Required when using reverse proxies like nginx or development tools
# These origins are trusted for CSRF token validation
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',  # Local development server
    'http://127.0.0.1:53694',  # Development tool port
    'http://localhost:8000',   # Alternative localhost
    'http://localhost:53694',  # Alternative development port
]

# Security settings for production environment
# These settings are only enabled when DEBUG=False
if not DEBUG:
    SECURE_SSL_REDIRECT = True         # Force HTTPS connections
    SESSION_COOKIE_SECURE = True      # Send cookies only over HTTPS
    CSRF_COOKIE_SECURE = True          # Send CSRF cookies only over HTTPS
    SECURE_HSTS_SECONDS = 31536000     # HTTP Strict Transport Security (1 year)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Apply HSTS to all subdomains
    SECURE_HSTS_PRELOAD = True          # Allow browser to preload HSTS settings
    X_FRAME_OPTIONS = 'DENY'           # Prevent clickjacking attacks

# ─────────────────────────────────────────────────────────────
# APPLICATION DEFINITION
# ─────────────────────────────────────────────────────────────

# Django applications to be loaded
# Order matters: custom app 'randini' comes after Django apps
INSTALLED_APPS = [
    'django.contrib.admin',         # Django admin interface
    'django.contrib.auth',          # Authentication system
    'django.contrib.contenttypes',  # Content type framework
    'django.contrib.sessions',      # Session framework
    'django.contrib.messages',      # Message framework
    'django.contrib.staticfiles',   # Static files management
    'randini'                       # Custom garage management app
]

# Middleware stack for request/response processing
# Order matters: SecurityMiddleware should be first
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # Security headers and SSL
    'django.contrib.sessions.middleware.SessionMiddleware',  # Session management
    'django.middleware.common.CommonMiddleware',            # Common utilities
    'django.middleware.csrf.CsrfViewMiddleware',           # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware', # User authentication
    'django.contrib.messages.middleware.MessageMiddleware',  # Flash messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Clickjacking protection
]

# Root URL configuration module
ROOT_URLCONF = 'randinigarage.urls'

# Template engine configuration
# Defines how Django renders HTML templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # Django template engine
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'randini.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'randinigarage.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'randinii_db',
        'USER': 'root',
        'PASSWORD': '2025',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
USE_TZ = False

TIME_ZONE = 'Africa/Nairobi'


USE_I18N = True



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Media files (Uploaded by users)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Email Configuration
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'randinigarage@gmail.com'
EMAIL_HOST_PASSWORD = 'podawfstzzqjrdbf'
DEFAULT_FROM_EMAIL = 'Randini Garage <randinigarage@gmail.com>'

# Logging Configuration
import os
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': config('LOG_LEVEL', default='INFO'),
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'randini': {
            'handlers': ['console'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}

# Add file handler only in production or when explicitly enabled
if not DEBUG or config('ENABLE_FILE_LOGGING', default=False, cast=bool):
    LOGGING['handlers']['file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': LOGS_DIR / 'django.log',
        'formatter': 'verbose',
    }
    LOGGING['root']['handlers'].append('file')
    LOGGING['loggers']['django']['handlers'].append('file')
    LOGGING['loggers']['randini']['handlers'].append('file')

# M-Pesa Configuration
MPESA_CALLBACK_URL = config('MPESA_CALLBACK_URL', default='https://yourdomain.com/mpesa-callback/')