import os
import django
from faker import Faker
from django.contrib.auth.hashers import make_password

# Indique où se trouve ton settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idealbooth_project.settings')
django.setup()

fake = Faker('fr_FR')

for i in range(100):
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = fake.email()
    phone = fake.phone_number()
    address = fake.address().replace('\n', ', ')
    password = make_password('Motdepasse123')
    date_joined = fake.date_time_this_decade().strftime('%Y-%m-%d %H:%M:%S')
    
    sql = f"""
    INSERT INTO accounts_customuser 
    (first_name, last_name, email, phone_number, address, password, is_active, date_joined, profile_picture) 
    VALUES 
    ('{first_name}', '{last_name}', '{email}', '{phone}', '{address}', '{password}', TRUE, '{date_joined}', NULL);
    """
    print(sql.strip())
