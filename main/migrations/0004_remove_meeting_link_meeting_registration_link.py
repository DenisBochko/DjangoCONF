# Generated by Django 5.2 on 2025-04-05 02:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_meeting_link_usermeetings'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meeting',
            name='link',
        ),
        migrations.AddField(
            model_name='meeting',
            name='registration_link',
            field=models.CharField(default='link', verbose_name='Ссылка на регистрацию на конференцию'),
            preserve_default=False,
        ),
    ]
