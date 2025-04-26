from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Campaign, CampaignEligibleCustomer, DiscountUsage
from .serializers import (
    CampaignSerializer, 
    DiscountUsageSerializer, 
    CartDiscountRequestSerializer,
    ApplyDiscountRequestSerializer,
)
from rest_framework.authentication import TokenAuthentication
from django.db.models import F

User = get_user_model()

class CampaignListCreateView(APIView):
    """
    API endpoint for listing and creating campaigns.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        campaigns = Campaign.objects.all()
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data)
    

    """

    ---------------cart discount payload--------

    {
    "name": "Summer Sale - 15% Off",
    "description": "Get 15% off on all orders",
    "discount_type": "CART",
    "discount_calculation": "PERCENTAGE",
    "discount_value": 15,
    "max_discount_amount": 30,
    "start_date": "2023-06-01T00:00:00Z",
    "end_date": "2023-06-30T23:59:59Z",
    "total_budget": 5000,
    "max_transactions_per_day": 2,
    "eligible_customer_ids": [101, 102, 103],
    "is_active": true
    }


    ------------Deleivery discount payload------------

    {
    "name": "Free Shipping Weekend",
    "description": "Free delivery on all orders",
    "discount_type": "DELIVERY",
    "discount_calculation": "FIXED",
    "discount_value": 5,
    "start_date": "2023-06-10T00:00:00Z",
    "end_date": "2023-06-11T23:59:59Z",
    "total_budget": 1000,
    "max_transactions_per_day": 1,
    "eligible_customer_ids": [45, 78, 112], 
    "is_active": true
    }

    """
    
    def post(self, request):
        serializer = CampaignSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampaignDetailView(APIView):
    """
    API endpoint for retrieving, updating, and deleting campaigns.
    """
    permission_classes = [IsAdminUser]
    
    def get_object(self, pk):
        try:
            return Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return None
    
    def get(self, request, pk):
        campaign = self.get_object(pk)
        if not campaign:
            return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CampaignSerializer(campaign)
        return Response(serializer.data)
    
    def put(self, request, pk):
        campaign = self.get_object(pk)
        if not campaign:
            return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CampaignSerializer(campaign, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        campaign = self.get_object(pk)
        if not campaign:
            return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CampaignSerializer(campaign, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        campaign = self.get_object(pk)
        if not campaign:
            return Response({"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND)
        
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailableCampaignsView(APIView):
    """
    API endpoint to fetch available discount campaigns based on cart parameters.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CartDiscountRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user_id = data.get('user_id')
        cart_total = data.get('cart_total')
        delivery_fee = data.get('delivery_fee')
        
        # Get current active campaigns
        now = timezone.now()
        active_campaigns = Campaign.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
            budget_used__lt=F('total_budget')
        )
        
        # Check for user-specific campaigns
        eligible_campaign_ids = list(CampaignEligibleCustomer.objects.filter(
            user_id=user_id
        ).values_list('campaign_id', flat=True))
        
        # If eligible campaigns exist for any campaign, filter by these
        restricted_campaigns = active_campaigns.filter(
            eligible_customers__isnull=False
        ).distinct()
        
        unrestricted_campaigns = active_campaigns.filter(
            eligible_customers__isnull=True
        )
        
        eligible_restricted_campaigns = restricted_campaigns.filter(
            id__in=eligible_campaign_ids
        )
        
        # Combine unrestricted and eligible restricted campaigns
        available_campaigns = unrestricted_campaigns.union(eligible_restricted_campaigns)
        # print("-------",available_campaigns)
        
        # Check daily usage limits
        result = []
        for campaign in available_campaigns:
            # print("------lop------",campaign.discount_type)
            usage_today = DiscountUsage.get_user_usage_today(campaign, User.objects.get(id=user_id))
            print("usage----",usage_today)
            
            if usage_today < campaign.max_transactions_per_day:
                campaign_data = CampaignSerializer(campaign).data
                
                # Calculate discount based on campaign type
                if campaign.discount_type == 'CART':
                    applicable_amount = cart_total
                else:  # DELIVERY
                    applicable_amount = delivery_fee
                
                discount_amount = campaign.calculate_discount(applicable_amount)
                campaign_data['calculated_discount'] = discount_amount
                campaign_data['applicable_to'] = campaign.discount_type.lower()
                # print("cap dtaa------",campaign_data)
                
                result.append(campaign_data)
                
        return Response(result)


class ApplyDiscountView(APIView):
    """
    API endpoint to apply a discount and record usage.
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = ApplyDiscountRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        user = data['user']
        campaign = data['campaign']
        cart_total = data.get('cart_total', 0)
        delivery_fee = data.get('delivery_fee', 0)
        transaction_id = data['transaction_id']
        
        # Validate campaign is active
        if not campaign.is_valid():
            return Response(
                {"error": "Campaign is not valid or has expired"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if campaign has user restrictions and if user is eligible
        has_restrictions = CampaignEligibleCustomer.objects.filter(campaign=campaign).exists()
        if has_restrictions:
            is_eligible = CampaignEligibleCustomer.objects.filter(campaign=campaign, user=user).exists()
            if not is_eligible:
                return Response(
                    {"error": "User is not eligible for this campaign"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check daily usage limit
        usage_today = DiscountUsage.get_user_usage_today(campaign, user)
        if usage_today >= campaign.max_transactions_per_day:
            return Response(
                {"error": "Daily usage limit reached for this campaign"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Calculate discount
        if campaign.discount_type == 'CART':
            applicable_amount = cart_total
        else:  # DELIVERY
            applicable_amount = delivery_fee
            
        discount_amount = campaign.calculate_discount(applicable_amount)
        
        # Check if enough budget remains
        if campaign.budget_used + discount_amount > campaign.total_budget:
            # If partial discount is possible
            remaining_budget = campaign.total_budget - campaign.budget_used
            if remaining_budget > 0:
                discount_amount = remaining_budget
            else:
                return Response(
                    {"error": "Campaign budget has been exhausted"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Record usage and update budget
        usage = DiscountUsage.objects.create(
            campaign=campaign,
            user=user,
            transaction_id=transaction_id,
            discount_amount=discount_amount
        )
        
        # Update campaign budget
        campaign.budget_used += discount_amount
        campaign.save()
        
        return Response({
            "success": True,
            "discount_applied": float(discount_amount),
            "remaining_campaign_budget": float(campaign.total_budget - campaign.budget_used)
        })


class DiscountUsageListView(APIView):
    """
    API endpoint to list discount usage records.
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Optional filtering
        campaign_id = request.query_params.get('campaign_id')
        user_id = request.query_params.get('user_id')
        
        usages = DiscountUsage.objects.all()
        
        if campaign_id:
            usages = usages.filter(campaign_id=campaign_id)
            
        if user_id:
            usages = usages.filter(user_id=user_id)
            
        serializer = DiscountUsageSerializer(usages, many=True)
        return Response(serializer.data)