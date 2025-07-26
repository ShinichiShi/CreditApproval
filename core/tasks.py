# core/tasks.py
from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from datetime import datetime
import logging
import traceback
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task
def import_customer_data():
    try:
        logger.info("Starting customer data import...")

        # Check if file exists
        import os

        if not os.path.exists("customer_data.xlsx"):
            logger.error("customer_data.xlsx file not found!")
            return {"success": False, "error": "File not found"}

        # Read Excel file
        df = pd.read_excel("customer_data.xlsx")
        logger.info(f"Read {len(df)} rows from customer_data.xlsx")

        # Check required columns
        required_columns = [
            "First Name",
            "Last Name",
            "Age",
            "Phone Number",
            "Monthly Salary",
            "Approved Limit",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing columns: {missing_columns}")
            return {"success": False, "error": f"Missing columns: {missing_columns}"}

        created_count = 0
        error_count = 0

        # Use transaction to ensure data consistency
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    Customer.objects.create(
                        first_name=row["First Name"],
                        last_name=row["Last Name"],
                        age=row["Age"],
                        phone_number=row["Phone Number"],
                        monthly_salary=row["Monthly Salary"],
                        approved_limit=row["Approved Limit"],
                        current_debt=0,
                    )
                    created_count += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"Error creating customer at row {index}: {str(e)}")
                    logger.error(f"Row data: {row.to_dict()}")

        logger.info(
            f"Customer import completed. Created: {created_count}, Errors: {error_count}"
        )
        return {
            "success": True,
            "created": created_count,
            "errors": error_count,
            "total_customers": Customer.objects.count(),
        }

    except Exception as e:
        logger.error(f"Fatal error in import_customer_data: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


@shared_task
def import_loan_data():
    try:
        logger.info("Starting loan data import...")
        df = pd.read_excel("loan_data.xlsx")
        logger.info(f"Loaded {len(df)} loan records")

        # Log column names for debugging
        logger.info(f"Excel columns: {list(df.columns)}")

        imported_count = 0
        skipped_count = 0
        error_count = 0

        # Handle potential column name variations
        column_mapping = {
            "Customer ID": ["Customer ID", "customer_id", "CustomerId"],
            "Loan ID": ["Loan ID", "loan_id", "LoanId"],
            "Loan Amount": ["Loan Amount", "loan_amount", "LoanAmount"],
            "Tenure": ["Tenure", "tenure"],
            "Interest Rate": ["Interest Rate", "interest_rate", "InterestRate"],
            "Monthly payment": [
                "Monthly payment",
                "Monthly Payment",
                "monthly_payment",
                "MonthlyPayment",
            ],
            "EMIs paid on Time": [
                "EMIs paid on Time",
                "EMIs_paid_on_Time",
                "emis_paid_on_time",
            ],
            "Date of Approval": [
                "Date of Approval",
                "date_of_approval",
                "DateOfApproval",
            ],
            "End Date": ["End Date", "end_date", "EndDate"],
        }

        # Find actual column names
        actual_columns = {}
        for standard_name, variations in column_mapping.items():
            for variation in variations:
                if variation in df.columns:
                    actual_columns[standard_name] = variation
                    break
            if standard_name not in actual_columns:
                logger.error(
                    f"Column '{standard_name}' not found. Available columns: {list(df.columns)}"
                )
                return {
                    "status": "error",
                    "message": f"Column {standard_name} not found",
                }

        logger.info(f"Column mapping: {actual_columns}")

        with transaction.atomic():
            for index, row in df.iterrows():
                loan_id = None
                try:
                    customer_id = row[actual_columns["Customer ID"]]
                    customer = Customer.objects.get(customer_id=customer_id)

                    loan_id = row[actual_columns["Loan ID"]]
                    if Loan.objects.filter(loan_id=loan_id).exists():
                        logger.warning(f"Loan {loan_id} already exists, skipping")
                        skipped_count += 1
                        continue

                    # Create loan
                    Loan.objects.create(
                        loan_id=loan_id,
                        customer=customer,
                        loan_amount=float(row[actual_columns["Loan Amount"]]),
                        tenure=int(row[actual_columns["Tenure"]]),
                        interest_rate=float(row[actual_columns["Interest Rate"]]),
                        monthly_payment=float(row[actual_columns["Monthly payment"]]),
                        emis_paid_on_time=int(row[actual_columns["EMIs paid on Time"]]),
                        start_date=pd.to_datetime(
                            row[actual_columns["Date of Approval"]]
                        ).date(),
                        end_date=pd.to_datetime(row[actual_columns["End Date"]]).date(),
                    )
                    imported_count += 1

                    if imported_count % 100 == 0:
                        logger.info(f"Imported {imported_count} loans so far...")

                except Customer.DoesNotExist:
                    logger.error(f"Customer {customer_id} not found for loan {loan_id}")
                    error_count += 1
                except Exception as e:
                    logger.error(f"Error importing loan {loan_id}: {str(e)}")
                    error_count += 1

        message = f"Loan import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}"
        logger.info(message)

        return {
            "status": "success",
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": error_count,
            "message": message,
        }

    except Exception as e:
        error_msg = f"Error importing loan data: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}


@shared_task
def check_data_status():
    """Debug task to check current database status"""
    try:
        customer_count = Customer.objects.count()
        loan_count = Loan.objects.count()

        logger.info(
            f"Database status - Customers: {customer_count}, Loans: {loan_count}"
        )

        # Get sample data
        sample_customers = list(Customer.objects.all()[:3].values())
        sample_loans = list(Loan.objects.all()[:3].values())

        return {
            "customer_count": customer_count,
            "loan_count": loan_count,
            "sample_customers": sample_customers,
            "sample_loans": sample_loans,
        }
    except Exception as e:
        logger.error(f"Error checking data status: {str(e)}")
        return {"error": str(e)}
