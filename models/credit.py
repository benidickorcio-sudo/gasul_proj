from datetime import datetime

from database import get_connection
from models.customer import get_customer_by_id, update_customer

DAILY_LATE_RATE = 0.0025      # 0.25% per day
WEEKLY_LATE_RATE = 0.0175     # 1.75% per week
MONTHLY_LATE_RATE = 0.05      # 5% per month


def calculate_late_charge(outstanding_amount, overdue_days):
    outstanding_amount = float(outstanding_amount or 0.0)
    if overdue_days <= 0 or outstanding_amount <= 0:
        return 0.0

    if overdue_days < 7:
        percent = DAILY_LATE_RATE * overdue_days
    elif overdue_days < 30:
        weeks = (overdue_days + 6) // 7
        percent = WEEKLY_LATE_RATE * weeks
    else:
        months = (overdue_days + 29) // 30
        percent = MONTHLY_LATE_RATE * months

    return round(outstanding_amount * percent, 2)


def apply_overdue_charges():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT sales_id, customer_id, total_amount, amount_paid, due_date, late_charge_applied
            FROM sales
            WHERE payment_method = 'CREDIT'
              AND status != 'PAID'
              AND due_date IS NOT NULL
              AND due_date < NOW()
            """
        )
        overdue_sales = cursor.fetchall()

        for sale in overdue_sales:
            if not sale.get("due_date"):
                continue

            outstanding = float(sale.get("total_amount", 0.0)) - float(sale.get("amount_paid", 0.0))
            if outstanding <= 0:
                continue

            due_date = sale["due_date"]
            overdue_days = (datetime.now().date() - due_date.date()).days
            if overdue_days <= 0:
                continue

            total_charge = calculate_late_charge(outstanding, overdue_days)
            already_applied = float(sale.get("late_charge_applied", 0.0) or 0.0)
            new_charge = round(max(0.0, total_charge - already_applied), 2)
            if new_charge <= 0:
                continue

            customer = get_customer_by_id(sale["customer_id"])
            if not customer:
                continue

            new_balance = float(customer.get("current_balance", 0.0) or 0.0) + new_charge
            update_customer(
                sale["customer_id"],
                name=customer.get("name", "Unknown"),
                current_balance=new_balance,
                conn=conn
            )

            cursor.execute(
                "UPDATE sales SET late_charge_applied = %s WHERE sales_id = %s",
                (already_applied + new_charge, sale["sales_id"])
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error applying overdue charges: {e}")
    finally:
        cursor.close()
        conn.close()


def add_charge(customer_id, amount, sale_id=None):
    customer = get_customer_by_id(customer_id)
    if customer is None:
        raise ValueError("Customer not found")

    current_balance = float(customer.get("current_balance", 0.0))
    updated = current_balance + float(amount)

    update_customer(customer_id, current_balance=updated)
    return updated


def add_payment(customer_id, amount, notes=None):
    customer = get_customer_by_id(customer_id)
    if customer is None:
        raise ValueError("Customer not found")

    current_balance = float(customer.get("current_balance", 0.0))
    updated = max(0.0, current_balance - float(amount))

    update_customer(customer_id, current_balance=updated)
    return updated


def get_customer_balance(customer_id):
    customer = get_customer_by_id(customer_id)
    return float(customer.get("current_balance", 0.0)) if customer else None