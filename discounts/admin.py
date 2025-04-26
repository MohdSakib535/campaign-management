from django.contrib import admin

# Register your models here.
from .models import Campaign,CampaignEligibleCustomer,DiscountUsage



admin.site.register(Campaign)
admin.site.register(CampaignEligibleCustomer)
admin.site.register(DiscountUsage)