from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_admin = models.BooleanField(default=False, verbose_name="Администратор")
    photo = models.ImageField(upload_to='user_photos/', null=True, blank=True, verbose_name="Фото")

    def __str__(self):
        return f"Профиль {self.user.username}"


class Meeting(models.Model):
    """Модель конференции"""
    registration_link = models.CharField(max_length=255, verbose_name="Ссылка на регистрацию на конференцию")
    name_room = models.CharField(max_length=255, verbose_name="Название комнаты")
    date = models.DateTimeField(verbose_name="Дата проведения")
    admin = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель конференции")

    def __str__(self):
        return f"Заседание {self.date}"


class UserMeetings(models.Model):
    """Связь пользователя и конференции"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user} - {self.meeting}"


class AgendaItem(models.Model):
    """Модель голосования"""
    meeting = models.ForeignKey(Meeting, related_name="agenda_items", on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name="Название вопроса")
    description = models.TextField(verbose_name="Описание вопроса")
    materials = models.FileField(
        upload_to='materials/',
        verbose_name="Материалы (подписаны ЭП)",
        null=True,  # Разрешаем NULL в базе данных
        blank=True  # Разрешаем пустое значение в формах
    )
    meeting_type = models.CharField(
        max_length=50,
        choices=[("vote", "Заочное голосование"), ("online", "Дистанционное участие")],
        verbose_name="Форма проведения"
    )
    summary_datetime = models.DateTimeField(
        verbose_name="Дата и время подведения итогов",
    )

    def __str__(self):
        return self.title


class Vote(models.Model):
    """Модель голосования по вопросу"""
    agenda_item = models.ForeignKey(AgendaItem, related_name="votes", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote = models.CharField(
        max_length=10,
        choices=[("yes", "За"), ("no", "Против"), ("abstain", "Воздержался")],
        verbose_name="Голос"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время голоса")
    signed_vote = models.FileField(
        upload_to='signed_votes/',
        verbose_name="Подписанный опросный лист (ЭП)",
        null=True,  # Разрешаем NULL в базе данных
        blank=True  # Разрешаем пустое значение в формах
    )

    def __str__(self):
        return f"{self.user.username} - {self.vote}"
