# Generated by Django 4.2 on 2023-10-09 15:24

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0021_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 11, 15, 24, 36, 54828, tzinfo=datetime.timezone.utc)),
        ),
    ]