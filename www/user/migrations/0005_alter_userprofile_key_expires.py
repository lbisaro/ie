# Generated by Django 4.2 on 2023-08-19 14:06

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 8, 21, 14, 6, 40, 500002, tzinfo=datetime.timezone.utc)),
        ),
    ]
