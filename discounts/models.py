from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Campaign(models.Model):
    """
    Model representing a discount campaign with constraints.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('CART', 'Cart Discount'),
        ('DELIVERY', 'Delivery Discount'),
    ]
    
    DISCOUNT_CALCULATION_CHOICES = [
        ('PERCENTAGE', 'Percentage Discount'),
        ('FIXED', 'Fixed Amount Discount'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_calculation = models.CharField(max_length=20, choices=DISCOUNT_CALCULATION_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Campaign duration and budget constraints
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    total_budget = models.DecimalField(max_digits=12, decimal_places=2)
    budget_used = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Usage constraints
    max_transactions_per_day = models.PositiveIntegerField(default=1)
    
    # Campaign status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def is_valid(self):
        """Check if campaign is currently valid based on date and budget"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date or now > self.end_date:
            return False
        if self.budget_used >= self.total_budget:
            return False
        return True

    def calculate_discount(self, amount):
        """Calculate discount amount based on discount type"""
        if self.discount_calculation == 'PERCENTAGE':
            discount = amount * (self.discount_value / 100)
        else:  # FIXED
            discount = self.discount_value
            
        # Apply max discount cap if set
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount
            
        return discount


class CampaignEligibleCustomer(models.Model):
    """
    Model to restrict campaigns to specific customers.
    If no records exist for a campaign, it's available to all customers.
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='eligible_customers')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('campaign', 'user')
        
    def __str__(self):
        return f"{self.campaign.name} - {self.user.username}"


class DiscountUsage(models.Model):
    """
    Model to track discount usage by customers for enforcement of usage limits.
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.campaign.name} - {self.user.username} - {self.used_at.date()}"
    
    @classmethod
    def get_user_usage_today(cls, campaign, user):
        """Get number of times user has used this campaign today"""
        today = timezone.now().date()
        return cls.objects.filter(
            campaign=campaign,
            user=user,
            used_at__date=today
        ).count()