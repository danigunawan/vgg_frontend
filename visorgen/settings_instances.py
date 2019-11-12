"""
Django settings for visorgen project.

Generated by 'django-admin startproject' using Django 1.10.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os

######
# Main paths
######

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DATA_DIR = '/webapps/visorgen/'

######
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/
######

# SECURITY WARNING: keep the secret key used in production secret!
# If you need to generate a new key, see https://pypi.python.org/pypi/django-generate-secret-key/1.0.2
with open( os.path.join(BASE_DIR, '..', 'secret_key_visorgen') )  as f:
    SECRET_KEY = f.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

######
# Application settings
######

# Site prefix, if changed:
#   - keep it with the same pattern '/<prefix>'
#   - needs to be replaced too in your web server proxy configuration file (if used).
SITE_PREFIX = "/vgg_frontend"

# Login URL
LOGIN_URL = SITE_PREFIX + '/login/'

# Allow bulk update of >1K objects
# https://docs.djangoproject.com/en/1.10/ref/settings/#data-upload-max-number-fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# Set a character to be a wildcard for keyword-based search.
# It should be JUST ONE CHARACTER and cannot be '#'.
KEYWORDS_WILDCARD = '*'

######
# Application definition
######

INSTALLED_APPS = [
    'siteroot',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'visorgen.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'visorgen.wsgi.application'


######
# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
######

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


######
# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators
######

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


######
# Cache settings
# https://docs.djangoproject.com/en/1.10/topics/cache/
######

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}


######
# Session settings
######

SESSION_ENGINE = "django.contrib.sessions.backends.file"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True


######
# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
######

LANGUAGE_CODE = 'en-uk'

TIME_ZONE = 'GB'

USE_I18N = True

USE_L10N = True

USE_TZ = True


######
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
######

STATIC_URL = SITE_PREFIX + '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'siteroot', 'static')


######
# Visor web site options
######

VISOR = {
    'title': 'My Visual Search Engine',
    'disable_autocomplete': True,
    'results_per_page' : 50,
    'check_backends_reachable': True,
    'select_roi' : True, # enable only when the selected backend is able to receive ROIs as input
    'enable_viewsel' : True, # enable only when the selected backend is able to return ROIs
    'datasets' : {  # Dictionary of datasets. Only one dataset at a time is supported.
                    # The key-name of the dataset is used to locate subfolders within
                    # the different PATHS used by the controller.

                    'mydataset' : 'Any dataset'
                 },
    'engines' : {

                # Sample backend engine for instance search.
                # It support images and text as input.
                'instances':{ 'full_name' : 'Instances',
                              'url': '/',
                              'backend_port' : 45288,
                              'imgtools_postproc_module' : 'visor_category',
                              'imgtools_style': 'photo',
                              'pattern_fname_classifier' : '${query_strid}.bin',
                              'can_save_uber_classifier': False,
                              'skip_query_progress': False,
                              'engine_for_similar_search': 'instances',
                              'improc_timeout': 5
                            },
                    },
}


# Folders used by the controller code
BASE_FRONTEND_DATA_DIR = os.path.join( BASE_DATA_DIR, 'frontend_data')
PATHS = {
    'classifiers' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'classifiers'),
    'postrainimgs' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'postrainimgs'),
    'uploadedimgs' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'uploadedimgs'),
    'rankinglists' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'rankinglists'),
    'predefined_rankinglists' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'predefined_rankinglists'),
    'postrainanno' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'postrainanno'),
    'postrainfeats' : os.path.join( BASE_FRONTEND_DATA_DIR, 'searchdata', 'postrainfeats'),
    'curatedtrainimgs' : os.path.join( BASE_FRONTEND_DATA_DIR, 'curatedtrainimgs'),
    'datasets' : os.path.join( BASE_DATA_DIR, 'datasets', 'images'),
    'thumbnails' : os.path.join( BASE_DATA_DIR, 'datasets', 'images'), # keep this one the same as 'datasets' unless thumbnails are really provided
    'regions' : os.path.join( BASE_DATA_DIR, 'datasets', 'images'), # The ROIs are defined over the original images
}

# Folders containing metadata
METADATA = {
    'metadata' : os.path.join( BASE_DATA_DIR, 'datasets', 'metadata')
}

# Settings of the visor engine
RETENGINE = {
    'pool_workers' : 8,
    'resize_width' : 560,
    'resize_height' : 420,
    'disable_cache' : False,
    'rf_rank_type' : 'full',
    'rf_rank_topn' : 2000,
    'rf_train_type' : 'regular',
}

# Settings for image search tool
IMSEARCHTOOLS = {
    'service_host' : 'localhost',
    'service_port' : 36213,
    'engine' : 'google_web',
    'query_timeout' : -1.0,
    'improc_timeout' : 8,
    'per_image_timeout' : 3.0,
    'num_pos_train' : 20,
}

# Base folder of scripts to manage the service
MANAGE_SERVICE_SCRIPTS_BASE_PATH = os.path.join(BASE_DIR, 'scripts')
