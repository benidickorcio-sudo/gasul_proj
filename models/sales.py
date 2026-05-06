from database import get_connection
from models.product import deduct_sale
from models.customer import get_customer_by_id, update_customer
from utils.auth import get_current_user
from datetime import datetime, timedelta


def log_transaction(sale_id, created_by, status, message):
    """Log a transaction to the transactions table."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (sale_id, created_by, status, message)
            VALUES (%s, %s, %s, %s)
        """, (sale_id, created_by, status, message))
        conn.commit()
    except Exception as e:
        print(f"Error logging transaction: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_sale(customer_id, items, payment_method, amount_paid, total_amount=None, actual_amount_received=None, due_date=None, created_by=None):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Calculate totals 
        if total_amount is None:
            total = 0
            for item in items:
                total = total + item["subtotal"]
            total_amount = total
        
        if actual_amount_received is not None:
            change_amount = float(actual_amount_received) - total_amount
            if change_amount < 0:
                change_amount = 0
        else:
            change_amount = float(amount_paid) - total_amount
            if change_amount < 0:
                change_amount = 0
        
        if payment_method == "CREDIT":
            status = "NOT PAID"
            if due_date is None:
                due_date = datetime.now() + timedelta(days=7)
        else:
            status = "PAID"
            due_date = None

        if created_by is None:
            current_user = get_current_user()
            if current_user:
                created_by = current_user.get("username")

        # 1. INSERT SALE
        cursor.execute("""
            INSERT INTO sales (customer_id, total_amount, payment_method, amount_paid, change_amount, status, due_date, late_charge_applied, created_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, total_amount, payment_method, amount_paid, change_amount, status, due_date, 0.00, created_by))
        
        sale_id = cursor.lastrowid

        # 2. INSERT SOLD ITEMS + DEDUCT INVENTORY
        for item in items:
            cursor.execute("""
                INSERT INTO sold_items (sale_id, product_id, quantity, unit_price, subtotal) 
                VALUES (%s, %s, %s, %s, %s)
            """, (sale_id, item["product_id"], item["quantity"], item["unit_price"], item["subtotal"]))
            
            deduct_sale(item["product_id"], item["quantity"], cursor=cursor, conn=conn)

        # 3. UPDATE CUSTOMER BALANCE (if credit)
        if payment_method == "CREDIT" and customer_id:
            customer = get_customer_by_id(customer_id)
            if customer:
                balance_due = total_amount - amount_paid
                new_balance = float(customer["current_balance"]) + balance_due
                # Pass the customer's current name along with the new balance
                update_customer(
                    customer_id, 
                    name=customer.get("name", "Unknown"),
                    current_balance=new_balance, 
                    conn=conn
                )

        conn.commit()
        
        # 4. LOG SUCCESSFUL TRANSACTION (after commit)
        log_transaction(sale_id, created_by, "SUCCESS", "Sale completed successfully.")
        
        return sale_id

    except Exception as e:
        conn.rollback()
        # Log failed transaction using separate connection
        log_transaction(None, created_by, "FAILED", str(e))
        raise Exception(f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def get_sales_history():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sales_view")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_money_flow_history():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM money_flow ORDER BY date ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows



def get_sales_history():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sales_view"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_money_flow_history():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM money_flow ORDER BY date ASC"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
