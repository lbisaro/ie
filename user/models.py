from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
import datetime

class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    activation_key = models.CharField(max_length=40, blank=True)
    key_expires = models.DateTimeField(default=timezone.now()+ datetime.timedelta(2))

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural='Perfiles de Usuario'
