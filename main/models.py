from django.db import models
from django.contrib.auth.models import User
from accounts.models import UserExtraFields


class Essays(models.Model):
    original_essay=models.CharField(max_length=128000)
    rephrased_essay=models.CharField(max_length=128000, null=True)
    timefield=models.DateTimeField(auto_now_add=True)
    user=models.ForeignKey(User, on_delete=models.CASCADE, null=True , related_name='essays')
    def __str__(self):
        return self.user.username + " " + str(self.timefield)

