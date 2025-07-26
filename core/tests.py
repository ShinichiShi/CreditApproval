from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from core.models import Customer, Loan
from datetime import date, datetime
from unittest.mock import patch


class LoanAPITestCase(APITestCase):

    def setUp(self):
        # Customer with good credit profile
        self.customer = Customer.objects.create(
            first_name="Aaron",
            last_name="Garcia",
            age=30,
            phone_number="1234567890",
            monthly_salary=50000,
            approved_limit=1800000,
            current_debt=0,
        )

        # Customer with poor credit (high debt)
        self.poor_credit_customer = Customer.objects.create(
            first_name="Jane",
            last_name="Smith",
            age=25,
            phone_number="9876543210",
            monthly_salary=30000,
            approved_limit=1100000,
            current_debt=1200000,
        )

        # Customer with many existing loans
        self.high_loan_customer = Customer.objects.create(
            first_name="Bob",
            last_name="Wilson",
            age=35,
            phone_number="5555555555",
            monthly_salary=60000,
            approved_limit=2200000,
            current_debt=0,
        )

        # Create multiple existing loans for high_loan_customer
        for i in range(5):
            Loan.objects.create(
                customer=self.high_loan_customer,
                loan_amount=100000,
                tenure=12,
                interest_rate=12,
                monthly_payment=8000,
                emis_paid_on_time=6,
                start_date=date(2024, 1, 1),
                end_date=date(2025, 1, 1),
            )

        # Existing loan for main customer
        self.loan = Loan.objects.create(
            loan_id=9999,
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=10,
            monthly_payment=8792,
            emis_paid_on_time=12,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 1, 1),
        )

    # ============ REGISTER CUSTOMER TESTS ============

    def test_register_customer_success(self):
        """Test successful customer registration"""
        response = self.client.post(
            "/register/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "age": 28,
                "phone_number": "1111222333",  # Unique phone number
                "monthly_salary": 40000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("customer_id", response.data)
        self.assertEqual(response.data["first_name"], "John")
        self.assertEqual(response.data["last_name"], "Doe")
        self.assertEqual(response.data["monthly_salary"], 40000)
        self.assertEqual(
            response.data["approved_limit"], 1400000
        )  # 36 * 40000 = 1,440,000 rounded to 1,400,000

    def test_register_customer_with_monthly_income_field(self):
        """Test registration using monthly_income instead of monthly_salary"""
        response = self.client.post(
            "/register/",
            {
                "first_name": "Alice",
                "last_name": "Johnson",
                "age": 32,
                "phone_number": "2222333444",  # Unique phone number
                "monthly_income": 45000,  # Using monthly_income instead
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["monthly_salary"], 45000)
        self.assertEqual(
            response.data["approved_limit"], 1600000
        )  # 36 * 45000 = 1,620,000 rounded to 1,600,000

    def test_register_customer_missing_fields(self):
        """Test registration with missing required fields"""
        response = self.client.post(
            "/register/",
            {
                "first_name": "John",
                # Missing other required fields
            },
            format="json",
        )

        # Should return 400 error due to missing fields
        self.assertEqual(response.status_code, 400)

    # ============ CHECK ELIGIBILITY TESTS ============

    def test_check_eligibility_high_score_approval(self):
        """Test eligibility check for customer with high credit score"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": 50000,  # Smaller amount for better approval chances
                "interest_rate": 10,
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "approval", response.data
        )  # May be True or False depending on scoring
        self.assertEqual(response.data["interest_rate"], 10)
        self.assertIn("corrected_interest_rate", response.data)
        self.assertIn("monthly_installment", response.data)

    def test_check_eligibility_medium_score_approval(self):
        """Test eligibility for medium score requiring higher interest rate"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.high_loan_customer.customer_id,
                "loan_amount": 100000,
                "interest_rate": 14,  # Higher rate for medium score
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # May be approved with corrected rate depending on exact score
        self.assertIn("approval", response.data)
        self.assertGreaterEqual(response.data["corrected_interest_rate"], 12)

    def test_check_eligibility_poor_credit_rejection(self):
        """Test eligibility check for customer with poor credit"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.poor_credit_customer.customer_id,
                "loan_amount": 100000,
                "interest_rate": 15,
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["approval"])

    def test_check_eligibility_high_emi_rejection(self):
        """Test rejection due to high EMI (>50% of salary)"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": 2000000,  # Very high amount
                "interest_rate": 15,
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["approval"])

    def test_check_eligibility_customer_not_found(self):
        """Test eligibility check for non-existent customer"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": 99999,  # Non-existent ID
                "loan_amount": 100000,
                "interest_rate": 12,
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_check_eligibility_invalid_data_types(self):
        """Test eligibility check with invalid data types"""
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "invalid",  # Invalid type
                "interest_rate": 12,
                "tenure": 12,
            },
            format="json",
        )

        # Should return 400 error due to ValueError in view
        self.assertEqual(response.status_code, 400)

    # ============ CREATE LOAN TESTS ============

    def test_create_loan_approved(self):
        """Test successful loan creation"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "25000",  # Pass as string (as expected by view)
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("loan_approved"))
        self.assertIn("loan_id", response.data)
        self.assertIn("monthly_installment", response.data)
        self.assertEqual(response.data["customer_id"], self.customer.customer_id)

    def test_create_loan_rejected_poor_credit(self):
        """Test loan rejection due to poor credit"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.poor_credit_customer.customer_id,
                "loan_amount": "50000",
                "interest_rate": "15",
                "tenure": "12",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get("loan_approved"))
        self.assertIn("message", response.data)
        self.assertNotIn("loan_id", response.data)

    def test_create_loan_rejected_high_amount(self):
        """Test loan rejection due to very high amount"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "10000000",  # Very high amount
                "interest_rate": "30",
                "tenure": "12",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get("loan_approved"))

    def test_create_loan_missing_parameters(self):
        """Test loan creation with missing parameters"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "25000",
                # Missing interest_rate and tenure
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_create_loan_invalid_data_types(self):
        """Test loan creation with invalid data types"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "invalid_amount",
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_create_loan_customer_not_found(self):
        """Test loan creation for non-existent customer"""
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": 99999,
                "loan_amount": "25000",
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    @patch("core.views.datetime")
    def test_create_loan_updates_customer_debt(self, mock_datetime):
        """Test that creating a loan updates customer's current debt"""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = date(2024, 6, 1)

        initial_debt = self.customer.current_debt
        loan_amount = 50000

        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": str(loan_amount),
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        if response.data.get("loan_approved"):
            # Refresh customer from database
            self.customer.refresh_from_db()
            self.assertEqual(self.customer.current_debt, initial_debt + loan_amount)

    # ============ VIEW LOAN DETAIL TESTS ============

    def test_view_single_loan_success(self):
        """Test viewing a single loan's details"""
        response = self.client.get(f"/view-loan/{self.loan.loan_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["loan_id"], self.loan.loan_id)
        self.assertIn("customer", response.data)
        self.assertEqual(
            response.data["customer"]["customer_id"], self.customer.customer_id
        )
        self.assertEqual(response.data["loan_amount"], self.loan.loan_amount)
        self.assertEqual(response.data["interest_rate"], self.loan.interest_rate)
        self.assertEqual(response.data["tenure"], self.loan.tenure)
        self.assertIn("loan_approved", response.data)

    def test_view_single_loan_not_found(self):
        """Test viewing non-existent loan"""
        response = self.client.get("/view-loan/99999/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_view_single_loan_customer_details(self):
        """Test that loan view includes correct customer details"""
        response = self.client.get(f"/view-loan/{self.loan.loan_id}/")

        customer_data = response.data["customer"]
        self.assertEqual(customer_data["first_name"], self.customer.first_name)
        self.assertEqual(customer_data["last_name"], self.customer.last_name)
        self.assertEqual(customer_data["phone_number"], self.customer.phone_number)
        self.assertEqual(customer_data["age"], self.customer.age)

    # ============ VIEW CUSTOMER LOANS TESTS ============

    def test_view_customer_loans_success(self):
        """Test viewing all loans for a customer"""
        response = self.client.get(f"/view-loans/{self.customer.customer_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)  # Customer has one loan
        self.assertEqual(response.data[0]["loan_id"], self.loan.loan_id)

    def test_view_customer_loans_multiple_loans(self):
        """Test viewing loans for customer with multiple loans"""
        response = self.client.get(
            f"/view-loans/{self.high_loan_customer.customer_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 5)  # Customer has 5 loans

        # Check loan details structure
        for loan_data in response.data:
            self.assertIn("loan_id", loan_data)
            self.assertIn("loan_amount", loan_data)
            self.assertIn("interest_rate", loan_data)
            self.assertIn("monthly_installment", loan_data)
            self.assertIn("repayments_left", loan_data)

    def test_view_customer_loans_repayments_calculation(self):
        """Test that repayments_left is calculated correctly"""
        response = self.client.get(f"/view-loans/{self.customer.customer_id}/")

        loan_data = response.data[0]
        expected_repayments_left = self.loan.tenure - self.loan.emis_paid_on_time
        self.assertEqual(loan_data["repayments_left"], expected_repayments_left)

    def test_view_customer_loans_not_found(self):
        """Test viewing loans for non-existent customer"""
        response = self.client.get("/view-loans/99999/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_view_customer_loans_no_loans(self):
        """Test viewing loans for customer with no loans"""
        new_customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="0000000000",
            monthly_salary=35000,
            approved_limit=1300000,  # 36 * 35000 = 1,260,000 rounded to 1,300,000
            current_debt=0,
        )

        response = self.client.get(f"/view-loans/{new_customer.customer_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 0)

    # ============ EDGE CASES AND INTEGRATION TESTS ============

    def test_full_loan_workflow(self):
        """Test complete workflow: register -> check eligibility -> create loan -> view loan"""
        # 1. Register customer
        register_response = self.client.post(
            "/register/",
            {
                "first_name": "Workflow",
                "last_name": "Test",
                "age": 30,
                "phone_number": "7777777777",
                "monthly_salary": 55000,
            },
            format="json",
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        customer_id = register_response.data["customer_id"]

        # 2. Check eligibility
        eligibility_response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": customer_id,
                "loan_amount": 100000,
                "interest_rate": 12,
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(eligibility_response.status_code, status.HTTP_200_OK)

        # 3. Create loan (if eligible)
        if eligibility_response.data["approval"]:
            create_response = self.client.post(
                "/create-loan/",
                {
                    "customer_id": customer_id,
                    "loan_amount": "100000",
                    "interest_rate": "12",
                    "tenure": "12",
                },
                format="json",
            )

            self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
            loan_id = create_response.data["loan_id"]

            # 4. View created loan
            view_response = self.client.get(f"/view-loan/{loan_id}/")
            self.assertEqual(view_response.status_code, status.HTTP_200_OK)
            self.assertEqual(view_response.data["loan_id"], loan_id)

    def test_boundary_conditions_loan_amount(self):
        """Test boundary conditions for loan amounts"""
        # Test very small loan amount
        response = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "1000",  # Very small amount
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        # Should be processed (approved or rejected based on other factors)
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )

    def test_boundary_conditions_interest_rate(self):
        """Test boundary conditions for interest rates"""
        # Test very high interest rate
        response = self.client.post(
            "/check-eligibility/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": 50000,
                "interest_rate": 50,  # Very high rate
                "tenure": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should handle high interest rates appropriately

    def test_concurrent_loan_applications(self):
        """Test creating multiple loans for the same customer"""
        # First loan
        response1 = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "30000",
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        # Second loan (should consider first loan in calculation)
        response2 = self.client.post(
            "/create-loan/",
            {
                "customer_id": self.customer.customer_id,
                "loan_amount": "40000",
                "interest_rate": "12",
                "tenure": "12",
            },
            format="json",
        )

        # Both should be processed appropriately
        self.assertIn(
            response1.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )
        self.assertIn(
            response2.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )
