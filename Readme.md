# Discount Campaign Service

A Django REST API service for managing discount campaigns with flexible constraints for e-commerce platforms.

## Overview

This service provides a comprehensive solution for businesses to create and manage discount campaigns with various constraints:

- Apply discounts to either the entire cart or just delivery charges
- Set campaign duration by days and total budget (whichever is reached first)
- Limit discount usage per customer per day
- Target specific customers with exclusive campaigns

## Features

### Campaign Management
- Create, read, update, and delete discount campaigns
- Support for percentage-based or fixed amount discounts
- Set maximum discount caps
- Configure campaign validity periods
- Control budget allocation and track usage

### Customer Targeting
- Create campaigns for all customers
- Create exclusive campaigns for specific customers
- Track and enforce usage limits

### Discount Types
- **Cart Discounts**: Apply to overall cart value
- **Delivery Discounts**: Apply specifically to delivery charges

### API Endpoints

#### Authentication
- `/v1/auth/register/`: Register a new user
- `/v1/auth/login/`: Login and obtain authentication token
- `/v1/auth/profile/`: View and update user profile
- `/v1/auth/list/`: List all users (admin only)

#### Campaign Management
- `/v1/discounts/campaigns/`: List all campaigns or create a new campaign
- `/v1//discounts/campaigns/<id>/`: Retrieve, update or delete a specific campaign

#### Discount Application
- `/v1/discounts/available-campaigns/`: Get available campaigns for a given cart/user
- `/v1/discounts/apply-discount/`: Apply a discount to a transaction
- `/v1/discounts/discount-usage/`: List discount usage records (admin only)

## Technology Stack

- **Backend**: Django/Django REST Framework
- **Authentication**: Token-based authentication
- **Database**: SQLite (default, can be configured for PostgreSQL, MySQL, etc.)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/discount-campaign-service.git
cd discount-campaign-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Apply migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## API Usage Examples

### Creating a Campaign

#### Cart Discount Example
```json
POST /api/discounts/campaigns/
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
```

#### Delivery Discount Example
```json
POST /v1/discounts/campaigns/
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
```

### Getting Available Campaigns

```json
POST v1/discounts/available-campaigns/
{
  "user_id": 123,
  "cart_total": 150.00,
  "delivery_fee": 5.00
}
```

### Applying a Discount

```json
POST /v1/discounts/apply-discount/
{
  "user_id": 123,
  "campaign_id": 1,
  "cart_total": 150.00,
  "delivery_fee": 5.00,
  "transaction_id": "order-12345-abc"
}
```

## Data Models

### Campaign
- **name**: Campaign identifier
- **description**: Campaign details
- **discount_type**: CART or DELIVERY
- **discount_calculation**: PERCENTAGE or FIXED
- **discount_value**: Amount or percentage to discount
- **max_discount_amount**: Optional cap on maximum discount
- **start_date/end_date**: Campaign validity period
- **total_budget**: Maximum budget allocated
- **budget_used**: Current used budget
- **max_transactions_per_day**: User daily usage limit
- **is_active**: Campaign status flag

### CampaignEligibleCustomer
- **campaign**: Reference to campaign
- **user**: Eligible user

### DiscountUsage
- **campaign**: Applied campaign
- **user**: User who used the discount
- **transaction_id**: Unique transaction identifier
- **discount_amount**: Amount discounted
- **used_at**: Timestamp of usage

## Authentication

The service uses token-based authentication:

1. Register a new user or login with existing credentials
2. Include the token in the Authorization header for protected endpoints:
   ```
   Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
   ```

## License

[MIT License](LICENSE)

## Contributors

- Your Name - Mohd Sakib