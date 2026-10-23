from django.db import models
from account.models import DarkAccount

# Create your models here.

# заявки в команду Dark.Tehno
class TeamApplication(models.Model):
    class Position(models.TextChoices):
        DEVELOPER = "developer", "Разработчик"
        DESIGNER = "designer", "Дизайнер"
        OTHER = "other", "Другое"

    user = models.ForeignKey(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="team_applications"
    )

    work_experience = models.TextField("Опыт работы", blank=True)
    skills = models.TextField("Навыки", blank=True)
    additional_info = models.TextField("Дополнительная информация", blank=True)
    social_links = models.TextField("Ссылки на соц. сети", blank=True)
    position = models.CharField(
        max_length=20,
        choices=Position.choices,
        default=Position.OTHER
    )
    page_example = models.FileField("Пример страницы", upload_to="team_applications/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Заявка от {self.user.username} (ID: {self.id})"


# Сотрудник команды Dark.Tehno
class TeamMember(models.Model):
    user = models.OneToOneField(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="team_member"
    )

    position = models.CharField(
        max_length=20,
        choices=TeamApplication.Position.choices,
        default=TeamApplication.Position.OTHER
    )

    joined_at = models.DateTimeField(auto_now_add=True)


# Задача для участника команды Dark.Tehno
class TeamTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "В ожидании"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершено"
        REJECTED = "rejected", "Отклонено"

    title = models.CharField("Название", max_length=255)
    description = models.TextField("Описание")
    assigned_to = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} (Статус: {self.status})"