#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'randinigarage.settings')

django.setup()

from django.contrib.auth.models import User

# Check existing users
users = User.objects.all()
print(f'Total users: {users.count()}')
for u in users:
    print(f'{u.username}: email={u.email}, staff={u.is_staff}, super={u.is_superuser}')

# If no superuser, create one
if not User.objects.filter(is_superuser=True).exists():
    print('Creating superuser...')
    user = User.objects.create_superuser('admin@example.com', 'admin@example.com', 'admin123')
    print('Superuser created: email admin@example.com / password admin123')
else:
    print('Superuser already exists.')