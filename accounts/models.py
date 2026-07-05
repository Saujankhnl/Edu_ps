from django.db import models
from django.contrib.auth.models import User


class Institution(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    institution_name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username