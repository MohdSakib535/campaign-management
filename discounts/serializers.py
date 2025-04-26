from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Campaign, CampaignEligibleCustomer, DiscountUsage

User = get_user_model()

class CampaignEligibleCustomerSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = CampaignEligibleCustomer
        fields = ['id', 'user', 'username']


class CampaignSerializer(serializers.ModelSerializer):
    eligible_customers = CampaignEligibleCustomerSerializer(many=True, read_only=True)
    eligible_customer_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        write_only=True,
        required=False,
        queryset=User.objects.all(),
        source='eligible_customers'
    )
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'description', 'discount_type', 'discount_calculation',
            'discount_value', 'max_discount_amount', 'start_date', 'end_date',
            'total_budget', 'budget_used', 'max_transactions_per_day',
            'is_active', 'created_at', 'updated_at', 'eligible_customers',
            'eligible_customer_ids'
        ]
        read_only_fields = ['budget_used', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate campaign data"""
        # Validate date range
        if data.get('start_date') and data.get('end_date') and data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        # Validate discount value for percentage
        if data.get('discount_calculation') == 'PERCENTAGE' and data.get('discount_value', 0) > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%")
            
        return data
    
    def create(self, validated_data):
        """Create campaign with eligible customers"""
        eligible_customers = validated_data.pop('eligible_customers', None)
        campaign = Campaign.objects.create(**validated_data)
        
        # Add eligible customers if specified
        if eligible_customers:
            for user in eligible_customers:
                CampaignEligibleCustomer.objects.create(campaign=campaign, user=user)
                
        return campaign
    
    def update(self, instance, validated_data):
        """Update campaign with eligible customers"""
        eligible_customers = validated_data.pop('eligible_customers', None)
        
        # Update campaign fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update eligible customers if provided
        if eligible_customers is not None:
            # Clear existing relationships
            instance.eligible_customers.all().delete()
            
            # Create new relationships
            for user in eligible_customers:
                CampaignEligibleCustomer.objects.create(campaign=instance, user=user)
                
        return instance


class DiscountUsageSerializer(serializers.ModelSerializer):
    campaign_name = serializers.ReadOnlyField(source='campaign.name')
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = DiscountUsage
        fields = ['id', 'campaign', 'campaign_name', 'user', 'username', 
                  'transaction_id', 'discount_amount', 'used_at']
        read_only_fields = ['used_at']


class CartDiscountRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_user_id(self, value):
        """Validate user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value


class ApplyDiscountRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    transaction_id = serializers.CharField(max_length=100)
    
    def validate(self, data):
        # Validate user exists
        try:
            data['user'] = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
            
        # Validate campaign exists
        try:
            data['campaign'] = Campaign.objects.get(id=data['campaign_id'])
        except Campaign.DoesNotExist:
            raise serializers.ValidationError("Campaign does not exist")
            
        # Check if transaction ID is unique
        if DiscountUsage.objects.filter(transaction_id=data['transaction_id']).exists():
            raise serializers.ValidationError("Transaction has already been processed")
            
        return data