from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    address = models.TextField()
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return self.user.username
