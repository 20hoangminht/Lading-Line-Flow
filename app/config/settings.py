"""Flow settings.

One settings file. Everything that differs between a laptop and a customer deployment comes from
environment variables, so there is nothing to remember and nothing to get wrong.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-local-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "documents",
    "review",
    "validation",
    "metering",
    "integrations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgresql://flow:flow@localhost:5432/flow")
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Flow settings -------------------------------------------------------------------------

AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "au.anthropic.claude-haiku-4-5-20251001-v1:0"
)
BEDROCK_ENABLED = os.environ.get("BEDROCK_ENABLED", "false").lower() == "true"

REVIEW_CONFIDENCE_THRESHOLD = float(os.environ.get("REVIEW_CONFIDENCE_THRESHOLD", "0.85"))

# The usage meter. Blank locally: the meter still records every document in the database, it
# simply sends nothing. See docs/decree-356-boundaries.md for what it may ever contain.
METER_ENDPOINT = os.environ.get("METER_ENDPOINT", "")
METER_SIGNING_KEY_ID = os.environ.get("METER_SIGNING_KEY_ID", "")

# Every host this application is permitted to talk to. Adding one without adding it to
# tests/test_egress_allowlist.py in the same commit fails the build.
EGRESS_ALLOWLIST = [
    f"bedrock-runtime.{AWS_REGION}.amazonaws.com",
    f"s3.{AWS_REGION}.amazonaws.com",
    f"secretsmanager.{AWS_REGION}.amazonaws.com",
    f"kms.{AWS_REGION}.amazonaws.com",
    f"logs.{AWS_REGION}.amazonaws.com",
    "meter.ladingline.com",
]
