# Generated by Django 4.2 on 2023-10-09 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0014_rename_max_drowdown_bot_max_drawdown_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estrategia',
            name='max_drawdown',
            field=models.FloatField(),
        ),
    ]
