from django.db import models


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=15, unique=True)
    monthly_salary = models.PositiveIntegerField()
    approved_limit = models.PositiveIntegerField()
    current_debt = models.FloatField(default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"


class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="loans"
    )
    loan_amount = models.FloatField()
    tenure = models.PositiveIntegerField(help_text="Tenure in months")
    interest_rate = models.FloatField(help_text="Annual interest rate (%)")
    monthly_payment = models.FloatField()
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Loan {self.loan_id} for {self.customer.first_name}"
