from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from datetime import datetime

@shared_task
def import_customer_data():
    df = pd.read_excel("customer_data.xlsx")
    for _, row in df.iterrows():
        Customer.objects.create(
            first_name=row['first_name'],
            last_name=row['last_name'],
            phone_number=row['phone_number'],
            monthly_salary=row['monthly_salary'],
            approved_limit=row['approved_limit'],
            current_debt=row['current_debt'],
            age=25  
        )

@shared_task
def import_loan_data():
    df = pd.read_excel("loan_data.xlsx")
    for _, row in df.iterrows():
        Loan.objects.create(
            customer_id=row['customer_id'],
            loan_amount=row['loan_amount'],
            interest_rate=row['interest_rate'],
            tenure=row['tenure'],
            emi=row['monthly payment'],
            emis_paid_on_time=row['EMIs paid on Time'],
            start_date=pd.to_datetime(row['Date of Approval']).date(),
            end_date=pd.to_datetime(row['End Date']).date()
        )
