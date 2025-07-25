from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer
from datetime import datetime, timedelta
from .utils import evaluate_loan_eligibility
from django.db.utils import IntegrityError

class RegisterCustomerView(APIView):
    def post(self, request):
        try:
            data = request.data
            salary = data.get("monthly_salary") or data.get("monthly_income")
            
            if not salary:
                return Response(
                    {"error": "monthly_salary or monthly_income is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'age', 'phone_number']
            for field in required_fields:
                if not data.get(field):
                    return Response(
                        {"error": f"{field} is required"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            try:
                salary = int(salary)
                age = int(data['age'])
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid data types for salary or age"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            approved_limit = round(36 * salary, -5) 

            customer = Customer.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                age=age,
                phone_number=data['phone_number'],
                monthly_salary=salary,
                approved_limit=approved_limit,
                current_debt=0,
            )
            serializer = CustomerSerializer(customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except IntegrityError as e:
            if 'phone_number' in str(e):
                return Response(
                    {"error": "Phone number already exists"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Database integrity error"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CheckEligibilityView(APIView):
    def post(self, request):
        try:
            data = request.data
            customer_id = data.get("customer_id")
            
            # Validate required fields
            if not customer_id:
                return Response(
                    {"error": "customer_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                loan_amount = float(data.get("loan_amount"))
                interest_rate = float(data.get("interest_rate"))
                tenure = int(data.get("tenure"))
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid data types for loan parameters"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

            loans = Loan.objects.filter(customer=customer)
            result = evaluate_loan_eligibility(customer, loan_amount, interest_rate, tenure, loans)

            return Response({
                "customer_id": customer.customer_id,
                "approval": result["approval"],
                "interest_rate": interest_rate,
                "corrected_interest_rate": result["corrected_interest_rate"],
                "tenure": tenure,
                "monthly_installment": result["monthly_installment"]
            })
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CreateLoanView(APIView):
    def post(self, request):
        try:
            data = request.data
            customer_id = data.get("customer_id")
            loan_amount = data.get("loan_amount")
            interest_rate = data.get("interest_rate")
            tenure = data.get("tenure")

            if not all([customer_id, loan_amount, interest_rate, tenure]):
                return Response({"error": "Missing required loan parameters."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                loan_amount = float(loan_amount)
                interest_rate = float(interest_rate)
                tenure = int(tenure)
            except ValueError:
                return Response({"error": "Invalid data types."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

            loans = Loan.objects.filter(customer=customer)
            result = evaluate_loan_eligibility(customer, loan_amount, interest_rate, tenure, loans)

            if not result["approval"]:
                return Response({
                    "customer_id": customer.customer_id,
                    "loan_approved": False,
                    "message": "Loan cannot be approved due to credit constraints.",
                    "monthly_installment": result["monthly_installment"]
                }, status=status.HTTP_200_OK)

            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=30 * tenure)

            loan = Loan.objects.create(
                customer=customer,
                loan_amount=loan_amount,
                tenure=tenure,
                interest_rate=result["corrected_interest_rate"],
                monthly_payment=result["monthly_installment"],
                emis_paid_on_time=0,
                start_date=start_date,
                end_date=end_date
            )

            customer.current_debt += loan_amount
            customer.save()

            return Response({
                "loan_id": loan.loan_id,
                "customer_id": customer.customer_id,
                "loan_approved": True,
                "message": "Loan approved successfully.",
                "monthly_installment": loan.monthly_payment
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ViewLoanDetail(APIView):
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND)

        customer = loan.customer
        is_approved = True  # or add logic if needed

        data = {
            "loan_id": loan.loan_id,
            "customer": {
                "customer_id": customer.customer_id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "phone_number": customer.phone_number,
                "age": customer.age,
            },
            "loan_approved": is_approved,
            "loan_amount": loan.loan_amount,
            "interest_rate": loan.interest_rate,
            "monthly_installment": loan.monthly_payment,
            "tenure": loan.tenure,
        }

        return Response(data, status=status.HTTP_200_OK)

class ViewCustomerLoans(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        loans = Loan.objects.filter(customer=customer)

        result = []
        for loan in loans:
            repayments_left = loan.tenure - loan.emis_paid_on_time
            result.append({
                "loan_id": loan.loan_id,
                "loan_amount": loan.loan_amount,
                "interest_rate": loan.interest_rate,
                "monthly_installment": loan.monthly_payment,
                "repayments_left": repayments_left
            })

        return Response(result, status=status.HTTP_200_OK)