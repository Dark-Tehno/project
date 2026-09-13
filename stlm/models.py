from django.db import models


class Participant(models.Model):
    verbose_name = 'Участник'
    verbose_name_plural = 'Участники'

    name = models.CharField(max_length=100, verbose_name='Имя')
    email = models.EmailField(unique=True, verbose_name='Email')
    avatar = models.ImageField(upload_to='stlm/avatars/', blank=True, null=True, verbose_name='Аватар')
    role = models.CharField(
        max_length=50,
        choices=[
            ('vocalist', 'Вокал'),
            ('guitarist', 'Гитара'),
            ('drummer', 'Барабаны'),
            ('lyricist', 'Тексты'),
            ('programmer', 'Кодер'),
            ('other', 'Другое'),
        ],
        default='other',
        verbose_name='Роль',
    )
    member_photo = models.CharField(max_length=255, blank=True, null=True, verbose_name='Фото участника')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Участник'
        verbose_name_plural = 'Участники'
        ordering = ['name']


class Music(models.Model):
    verbose_name = 'Музыка'
    verbose_name_plural = 'Музыка'

    title = models.CharField(max_length=200, verbose_name='Название')
    release_date = models.DateField(verbose_name='Дата релиза')
    image = models.ImageField(upload_to='stlm/music/', blank=True, null=True, verbose_name='Изображение')
    file = models.FileField(upload_to='stlm/music_files/', blank=True, null=True, verbose_name='Файл')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    duration = models.DurationField(blank=True, null=True, verbose_name='Длительность')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Музыку'
        verbose_name_plural = 'Музыка'
        ordering = ['-release_date', 'title']


class Album(models.Model):
    verbose_name = 'Альбом'
    verbose_name_plural = 'Альбомы'

    title = models.CharField(max_length=200, verbose_name='Название')
    release_date = models.DateField(verbose_name='Дата релиза')
    image = models.ImageField(upload_to='stlm/albums/', blank=True, null=True, verbose_name='Изображение')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    music = models.ManyToManyField(Music, blank=True, verbose_name='Музыка')
    type = models.CharField(
        max_length=50,
        choices=[
            ('album', 'Альбом'),
            ('single', 'Сингл'),
            ('debut', 'дебют'),
        ],
        default='album',
        verbose_name='Тип',
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Альбом'
        verbose_name_plural = 'Альбомы'
        ordering = ['-release_date', 'title']


class Concert(models.Model):
    verbose_name = 'Концерт'
    verbose_name_plural = 'Концерты'

    date = models.DateField(verbose_name='Дата')
    start_time = models.TimeField(verbose_name='Время начала')
    city = models.CharField(max_length=100, verbose_name='Город')
    location = models.CharField(max_length=200, verbose_name='Место')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    image = models.ImageField(upload_to='stlm/concerts/', blank=True, null=True, verbose_name='Изображение')
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Цена')
    status = models.CharField(
        max_length=50,
        choices=[
            ('upcoming', 'Предстоящий'),
            ('past', 'Прошедший'),
            ('cancelled', 'Отменённый'),
        ],
        default='upcoming',
        verbose_name='Статус',
    )

    def __str__(self):
        return f"{self.city} - {self.date} ({self.status})"

    class Meta:
        verbose_name = 'Концерт'
        verbose_name_plural = 'Концерты'
        ordering = ['date', 'start_time']


class Merch(models.Model):
    verbose_name = 'Товар'
    verbose_name_plural = 'Товары'

    name = models.CharField(max_length=200, verbose_name='Название')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    image = models.ImageField(upload_to='stlm/merch/', blank=True, null=True, verbose_name='Изображение')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='Количество на складе')
    type = models.CharField(
        max_length=50,
        choices=[
            ('tshirt', 'Одежда'),
            ('poster', 'Плакат'),
            ('sticker', 'Стикер'),
            ('other', 'Другое'),
        ],
        default='other',
        verbose_name='Тип',
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']


class News(models.Model):
    verbose_name = 'Новость'
    verbose_name_plural = 'Новости'

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержимое')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-created_at']