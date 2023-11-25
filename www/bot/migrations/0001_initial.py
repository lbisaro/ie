# Generated by Django 4.2 on 2023-08-19 13:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parametros', models.TextField()),
                ('creado', models.DateField(default=django.utils.timezone.now)),
                ('activo', models.IntegerField(default=0)),
                ('interval_id', models.CharField(max_length=50)),
                ('quote_qty', models.DecimalField(decimal_places=8, max_digits=18)),
            ],
        ),
        migrations.CreateModel(
            name='Estrategia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('clase', models.SlugField()),
                ('parametros', models.TextField()),
                ('creado', models.DateField(default=django.utils.timezone.now)),
                ('activo', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Symbol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=16)),
                ('base_asset', models.CharField(max_length=8)),
                ('quote_asset', models.CharField(max_length=8)),
                ('qty_decs_qty', models.IntegerField(max_length=2)),
                ('qty_decs_price', models.IntegerField(max_length=2)),
                ('qty_decs_quote', models.IntegerField(max_length=2)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateField(default=django.utils.timezone.now)),
                ('base_asset', models.CharField(db_index=True, max_length=14)),
                ('quote_asset', models.CharField(db_index=True, max_length=14)),
                ('side', models.IntegerField(db_index=True, default=0)),
                ('completed', models.IntegerField(db_index=True, default=0)),
                ('qty', models.DecimalField(decimal_places=8, max_digits=15)),
                ('price', models.DecimalField(decimal_places=8, max_digits=15)),
                ('orderid', models.CharField(db_index=True, max_length=20, unique=True)),
                ('pos_order_id', models.IntegerField(db_index=True, default=0)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.bot')),
            ],
            options={
                'verbose_name_plural': 'Bots',
            },
        ),
        migrations.CreateModel(
            name='Klines',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado', models.DateField(db_index=True)),
                ('open', models.DecimalField(decimal_places=8, max_digits=15)),
                ('close', models.DecimalField(decimal_places=8, max_digits=15)),
                ('high', models.DecimalField(decimal_places=8, max_digits=15)),
                ('low', models.DecimalField(decimal_places=8, max_digits=15)),
                ('volume', models.DecimalField(decimal_places=2, max_digits=12)),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.symbol')),
            ],
        ),
        migrations.AddField(
            model_name='bot',
            name='estrategia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.estrategia'),
        ),
        migrations.AddField(
            model_name='bot',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]