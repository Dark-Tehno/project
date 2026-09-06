from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings

import os
import random


def portfolio(request):
    logo_url = f"/static/images/og/{random.randint(0, 9)}.png"
    return render(request, 'portfolio/index.html', {'logo_url': logo_url})

def darklang(request):
    return render(request, 'portfolio/darklang.html')


birthday_greetings = [
    "С Днем Рождения! Желаю всего самого наилучшего!",
    "Поздравляю с Днем Рождения! Пусть этот день будет наполнен радостью и улыбками.",
    "С Днем Рождения! Желаю счастья, здоровья, любви и успехов во всех начинаниях!",
    "Поздравляю с Днем Рождения! Пусть каждый день будет ярким и запоминающимся, как этот!",
    "С Днем Рождения! Помни, возраст - это всего лишь количество лет, которые мир наслаждается твоим присутствием!",
    "С Днем Рождения, дорогой/ая! Ты делаешь мир лучше своим присутствием.",
    "С Днем Рождения! Пусть этот год станет годом новых возможностей и свершений!",
    "С Днем Рождения, друг/подруга! Спасибо за то, что ты есть в моей жизни.",
    "С Днем Рождения! Пусть этот день будет полон веселья, подарков и приятных сюрпризов!"
]

month = {
    '01': "января",
    '02': "февраля",
    '03': "марта",
    '04': "апреля",
    '05': "мая",
    '06': "июня",
    '07': "июля",
    '08': "августа",
    '09': "сентября",
    '10': "октября",
    '11': "ноября",
    '12': "декабря"
    }

def birthday(request, name, date):
    greeting1 = random.choice(birthday_greetings)
    greeting2 = random.choice(birthday_greetings)
    date_parts = date.split('.')
    if len(date_parts) > 1 and date_parts[1] in month:
        date_parts[1] = month[date_parts[1]]
    date = ' '.join(date_parts)
    
    context = {
        'name': name,
        'date': date,
        'greeting1': greeting1,
        'greeting2': greeting2
    }
    return render(request, 'portfolio/birthday.html', context=context)



def favicon(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'favicon.png')
    with open(favicon_path, 'rb') as favicon_file:
        return HttpResponse(favicon_file.read(), content_type='image/x-icon')

def robots(request):
    """
    Генерирует содержимое файла robots.txt.
    Запрещает индексацию служебных, пользовательских и API-разделов.
    Разрешает доступ к статическим файлам и медиа, чтобы поисковики могли корректно рендерить страницы.
    """

    robots_content = f"""
User-agent: *

Disallow: /admin/
Disallow: /media/
Disallow: /account/*
Allow: /news/*
Allow: /DZ/*
Allow: /birthday/vsp210/21.01
Allow: /

Host: vsp210.ru
"""

    return HttpResponse(robots_content, content_type='text/plain')
