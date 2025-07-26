from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer
from datetime import datetime, timedelta
from .utils import evaluate_loan_eligibility
from django.db.utils import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Swagger parameter definitions
customer_id_param = openapi.Parameter(
    'customer_id',
    openapi.IN_QUERY,
    description="Customer ID",
    type=openapi.TYPE_INTEGER,
    required=True
)

loan_id_param = openapi.Parameter(
    'loan_id',
    openapi.IN_PATH,
    description="Loan ID",
    type=openapi.TYPE_INTEGER,
    required=True
)

# Request body schemas
register_customer_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['first_name', 'last_name', 'age', 'phone_number', 'monthly_salary'],
    properties={
        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Customer first name'),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Customer last name'),
        'age': openapi.Schema(type=openapi.TYPE_INTEGER, description='Customer age'),
        'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number (must be unique)'),
        'monthly_salary': openapi.Schema(type=openapi.TYPE_INTEGER, description='Monthly salary in rupees'),
        'monthly_income': openapi.Schema(type=openapi.TYPE_INTEGER, description='Alternative to monthly_salary'),
    },
    example={
        "first_name": "John",
        "last_name": "Doe", 
        "age": 30,
        "phone_number": "9876543210",
        "monthly_salary": 50000
    }
)

check_eligibility_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['customer_id', 'loan_amount', 'interest_rate', 'tenure'],
    properties={
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Customer ID'),
        'loan_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Loan amount requested'),
        'interest_rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='Interest rate requested'),
        'tenure': openapi.Schema(type=openapi.TYPE_INTEGER, description='Loan tenure in months'),
    },
    example={
        "customer_id": 87,
        "loan_amount": 4000,
        "interest_rate": 12.5,
        "tenure": 12
    }
)

create_loan_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['customer_id', 'loan_amount', 'interest_rate', 'tenure'],
    properties={
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Customer ID'),
        'loan_amount': openapi.Schema(type=openapi.TYPE_STRING, description='Loan amount as string'),
        'interest_rate': openapi.Schema(type=openapi.TYPE_STRING, description='Interest rate as string'),
        'tenure': openapi.Schema(type=openapi.TYPE_STRING, description='Loan tenure in months as string'),
    },
    example={
        "customer_id": 87,
        "loan_amount": "4000",
        "interest_rate": "12.5",
        "tenure": "12"
    }
)

# Response schemas
register_customer_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Generated customer ID'),
        'first_name': openapi.Schema(type=openapi.TYPE_STRING),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING),
        'age': openapi.Schema(type=openapi.TYPE_INTEGER),
        'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
        'monthly_salary': openapi.Schema(type=openapi.TYPE_INTEGER),
        'approved_limit': openapi.Schema(type=openapi.TYPE_INTEGER, description='Approved credit limit'),
        'current_debt': openapi.Schema(type=openapi.TYPE_INTEGER),
    }
)

eligibility_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'approval': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Whether loan is approved'),
        'interest_rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='Original requested interest rate'),
        'corrected_interest_rate': openapi.Schema(type=openapi.TYPE_NUMBER, description='System corrected interest rate'),
        'tenure': openapi.Schema(type=openapi.TYPE_INTEGER),
        'monthly_installment': openapi.Schema(type=openapi.TYPE_NUMBER, description='Calculated monthly EMI'),
    }
)

loan_approved_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'loan_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Generated loan ID'),
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'loan_approved': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'message': openapi.Schema(type=openapi.TYPE_STRING),
        'monthly_installment': openapi.Schema(type=openapi.TYPE_NUMBER),
    }
)

loan_rejected_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'loan_approved': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'message': openapi.Schema(type=openapi.TYPE_STRING),
        'monthly_installment': openapi.Schema(type=openapi.TYPE_NUMBER),
    }
)

loan_detail_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'loan_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'customer': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'customer_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'age': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        'loan_approved': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'loan_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
        'interest_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
        'monthly_installment': openapi.Schema(type=openapi.TYPE_NUMBER),
        'tenure': openapi.Schema(type=openapi.TYPE_INTEGER),
    }
)

customer_loans_response = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'loan_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'loan_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
            'interest_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
            'monthly_installment': openapi.Schema(type=openapi.TYPE_NUMBER),
            'repayments_left': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of EMIs remaining'),
        }
    )
)

error_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message'),
    }
)

class RegisterCustomerView(APIView):
    @swagger_auto_schema(
        operation_id='register_customer',
        operation_summary='Register a new customer',
        operation_description='''
        Register a new customer in the system with their personal and financial details.
        
        The system will automatically calculate the approved credit limit as 36 times 
        the monthly salary, rounded to the nearest lakh (100,000).
        
        **Business Logic:**
        - Approved limit = round(36 × monthly_salary, -5)
        - Phone number must be unique
        - Current debt starts at 0
        ''',
        request_body=register_customer_request,
        responses={
            201: openapi.Response('Customer registered successfully', register_customer_response),
            400: openapi.Response('Bad request - validation errors', error_response),
        },
        tags=['Customer Management']
    )
    def post(self, request):
        try:
            data = request.data
            salary = data.get("monthly_salary") or data.get("monthly_income")
            
            if not salary:
                return Response(
                    {"error": "monthly_salary or monthly_income is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
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
    @swagger_auto_schema(
        operation_id='check_loan_eligibility',
        operation_summary='Check loan eligibility for a customer',
        operation_description='''
        Check if a customer is eligible for a loan based on their credit history and profile.
        
        **Credit Scoring Algorithm:**
        1. **Payment History (0-25 points):** Based on past EMI payment performance
        2. **Number of Loans (0-20 points):** Penalty for having too many loans
        3. **Loan Activity (0-20 points):** Penalty for loans taken in current year
        4. **Loan Volume (0-20 points):** Based on current loan volume vs approved limit
        5. **Debt Check:** Automatic rejection if current debt > approved limit
        
        **Approval Logic:**
        - Score > 50: Approved with requested rate
        - Score 30-50: Approved only if rate ≥ 12%
        - Score 10-30: Approved only if rate ≥ 16%
        - Score ≤ 10: Rejected
        
        **EMI Check:** Rejected if total EMIs > 50% of monthly salary
        ''',
        request_body=check_eligibility_request,
        responses={
            200: openapi.Response('Eligibility check completed', eligibility_response),
            400: openapi.Response('Bad request - invalid parameters', error_response),
            404: openapi.Response('Customer not found', error_response),
        },
        tags=['Loan Processing']
    )
    def post(self, request):
        try:
            data = request.data
            customer_id = data.get("customer_id")
            
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
    @swagger_auto_schema(
        operation_id='create_loan',
        operation_summary='Create a new loan',
        operation_description='''
        Create a new loan for a customer after checking eligibility.
        
        **Process:**
        1. Validates all input parameters
        2. Checks customer credit eligibility
        3. If approved, creates loan record and updates customer debt
        4. Returns loan details with generated loan ID
        
        **Note:** All numeric parameters should be passed as strings.
        
        **Side Effects:**
        - Updates customer's current_debt upon approval
        - Creates new loan record with start_date = today
        - Sets end_date = start_date + (30 × tenure) days
        ''',
        request_body=create_loan_request,
        responses={
            201: openapi.Response('Loan approved and created', loan_approved_response),
            200: openapi.Response('Loan application rejected', loan_rejected_response),
            400: openapi.Response('Bad request - validation errors', error_response),
            404: openapi.Response('Customer not found', error_response),
        },
        tags=['Loan Processing']
    )
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
    @swagger_auto_schema(
        operation_id='get_loan_details',
        operation_summary='Get details of a specific loan',
        operation_description='''
        Retrieve detailed information about a specific loan including customer details.
        
        **Returns:**
        - Complete loan information
        - Associated customer details
        - Current loan status
        ''',
        manual_parameters=[
            openapi.Parameter(
                'loan_id',
                openapi.IN_PATH,
                description="Unique loan identifier",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response('Loan details retrieved successfully', loan_detail_response),
            404: openapi.Response('Loan not found', error_response),
        },
        tags=['Loan Information']
    )
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND)

        customer = loan.customer
        is_approved = True 

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
    @swagger_auto_schema(
        operation_id='get_customer_loans',
        operation_summary='Get all loans for a specific customer',
        operation_description='''
        Retrieve a list of all loans associated with a specific customer.
        
        **Returns:**
        - List of all customer loans
        - Current repayment status for each loan
        - Remaining EMIs for each loan
        
        **Repayments Left Calculation:**
        repayments_left = tenure - emis_paid_on_time
        ''',
        manual_parameters=[
            openapi.Parameter(
                'customer_id',
                openapi.IN_PATH,
                description="Unique customer identifier",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response('Customer loans retrieved successfully', customer_loans_response),
            404: openapi.Response('Customer not found', error_response),
        },
        tags=['Loan Information']
    )
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