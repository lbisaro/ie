# Generated by Django 4.2 on 2023-10-04 16:31

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0013_alter_userprofile_key_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='key_expires',
            field=models.DateTimeField(default=datetime.datetime(2023, 10, 6, 16, 31, 33, 727635, tzinfo=datetime.timezone.utc)),
        ),
    ]