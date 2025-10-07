from django.db import models

# Create your models here.

# Offer model

class Offer(models.Model):
    title = models.CharField(max_length=255)
    offer_percent = models.DecimalField(max_digits=5, decimal_places=2) 
    about = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_listed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.offer_percent}%)"
    

# Category model

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    offer = models.ForeignKey(
        Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name="categories"
    ) 
    is_list = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
