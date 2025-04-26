from django.urls import path
from .views import (
    CampaignListCreateView, 
    CampaignDetailView,
    AvailableCampaignsView,
    ApplyDiscountView,
    DiscountUsageListView
)

urlpatterns = [
    path('campaigns/', CampaignListCreateView.as_view(), name='campaign-list-create'),
    path('campaigns/<int:pk>/', CampaignDetailView.as_view(), name='campaign-detail'),
    path('available-campaigns/', AvailableCampaignsView.as_view(), name='available-campaigns'),
    path('apply-discount/', ApplyDiscountView.as_view(), name='apply-discount'),
    path('discount-usage/', DiscountUsageListView.as_view(), name='discount-usage-list'),
]