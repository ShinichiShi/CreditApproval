from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer
import math
from datetime import datetime

class RegisterCustomerView(APIView):
    def post(self, request):
        data = request.data
        salary = data.get("monthly_salary") or data.get("monthly_income")
        approved_limit = round(36 * int(salary), -5) 

        customer = Customer.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            age=data['age'],
            phone_number=data['phone_number'],
            monthly_salary=salary,
            approved_limit=approved_limit,
            current_debt=0,
        )
        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CheckEligibilityView(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get("customer_id")
        loan_amount = data.get("loan_amount")
        interest_rate = data.get("interest_rate")
        tenure = data.get("tenure")

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=404)

        loans = Loan.objects.filter(customer=customer)
        total_loan_volume = sum([loan.loan_amount for loan in loans])
        total_emis = sum([loan.monthly_payment for loan in loans])
        current_year_loans = loans.filter(start_date__year=datetime.now().year)

        # Base score
        score = 0

        if loans.exists():
            on_time_ratio = sum([loan.emis_paid_on_time for loan in loans]) / sum([loan.tenure for loan in loans])
            score += min(25, on_time_ratio * 25)
        else:
            score += 10  # some base trust

        score += max(0, 20 - len(loans)*2)
        score += max(0, 20 - len(current_year_loans)*5)
        score += max(0, 20 - (total_loan_volume / customer.approved_limit) * 20)

        if customer.current_debt > customer.approved_limit:
            score = 0

        approved = False
        corrected_rate = interest_rate

        if score > 50:
            approved = True
        elif score > 30 and interest_rate >= 12:
            approved = True
        elif score > 10 and interest_rate >= 16:
            approved = True
        elif score <= 10:
            approved = False

        if score <= 10:
            corrected_rate = 16
        elif score <= 30:
            corrected_rate = max(interest_rate, 16)
        elif score <= 50:
            corrected_rate = max(interest_rate, 12)

        monthly_rate = corrected_rate / (12 * 100)
        emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)

        if emi + total_emis > 0.5 * customer.monthly_salary:
            approved = False

        return Response({
            "customer_id": customer.customer_id,
            "approval": approved,
            "interest_rate": interest_rate,
            "corrected_interest_rate": corrected_rate,
            "tenure": tenure,
            "monthly_installment": round(emi, 2)
        })