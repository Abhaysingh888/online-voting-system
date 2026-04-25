#!/usr/bin/env bash
#!/usr/bin/env bash
#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input

echo "
import os
from django.contrib.auth.models import User

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'Uday123')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gmail.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

# Banao agar nahi hai
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print('Created!')

# Permissions force karo — har baar
user = User.objects.get(username=username)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password(password)
user.save()
print('Permissions + password updated!')
" | python manage.py shell