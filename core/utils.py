from datetime import datetime

def evaluate_loan_eligibility(customer, loan_amount, interest_rate, tenure, existing_loans):
    total_loan_volume = sum([loan.loan_amount for loan in existing_loans])
    total_emis = sum([loan.monthly_payment for loan in existing_loans])
    current_year_loans = existing_loans.filter(start_date__year=datetime.now().year)

    score = 0
    if existing_loans.exists():
        on_time_ratio = sum([loan.emis_paid_on_time for loan in existing_loans]) / sum([loan.tenure for loan in existing_loans])
        score += min(25, on_time_ratio * 25)
    else:
        score += 10

    score += max(0, 20 - len(existing_loans)*2)
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

    return {
        "score": score,
        "approval": approved,
        "corrected_interest_rate": corrected_rate,
        "monthly_installment": round(emi, 2)
    }
