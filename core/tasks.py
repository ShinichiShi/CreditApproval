from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from datetime import datetime

@shared_task
def import_customer_data():
    df = pd.read_excel("customer_data.xlsx")
    for _, row in df.iterrows():
        Customer.objects.create(
            first_name=row['First Name'],
            last_name=row['Last Name'],
            age=row['Age'],
            phone_number=row['Phone Number'],
            monthly_salary=row['Monthly Salary'],
            approved_limit=row['Approved Limit'],
            current_debt=0 
        )
@shared_task
def import_loan_data():
    df = pd.read_excel("loan_data.xlsx")
    for _, row in df.iterrows():
        Loan.objects.create(
            loan_id=row['Loan ID'],
            customer_id=row['Customer ID'],
            loan_amount=row['Loan Amount'],
            tenure=row['Tenure'],
            interest_rate=row['Interest Rate'],
            monthly_payment=row['Monthly payment'],
            emis_paid_on_time=row['EMIs paid on Time'],
            start_date=pd.to_datetime(row['Date of Approval']).date(),
            end_date=pd.to_datetime(row['End Date']).date()
        )