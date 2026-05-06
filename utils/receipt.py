from PIL import Image, ImageDraw, ImageFont
from database import get_connection
from datetime import datetime


def get_sale_data(sale_id):
    """Fetch sale details from database"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get sale info
        cursor.execute(
            """SELECT s.sales_id, s.sale_date, COALESCE(c.name) as customer_name,
                    s.total_amount, s.amount_paid, s.change_amount, s.payment_method, s.due_date
                FROM sales s
                LEFT JOIN customers c ON s.customer_id = c.customer_id
                WHERE s.sales_id = %s""",
            (sale_id,)
        )
        sale = cursor.fetchone()
        
        if not sale:
            cursor.close()
            conn.close()
            return None
        
        # Get sale items
        cursor.execute(
            """SELECT p.name as product_name, si.quantity, si.unit_price, si.subtotal
                FROM sold_items si
                JOIN products p ON si.product_id = p.product_id
                WHERE si.sale_id = %s""",
            (sale_id,)
        )
        items = cursor.fetchall()
        
        sale['items'] = items
        cursor.close()
        conn.close()
        return sale
    except Exception as e:
        print(f"Error fetching sale data: {e}")
        cursor.close()
        conn.close()
        return None


def generate_receipt(sale_data):
    """Generate receipt as PIL Image with important details"""
    width, height = 400, 500 + (len(sale_data['items']) * 30)
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 14)
        font_normal = ImageFont.truetype("arial.ttf", 11)
        font_small = ImageFont.truetype("arial.ttf", 9)
    except:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 10
    
    # Header
    draw.text((80, y), "ERMITA GASUL REFILLING STATION", fill="black", font=font_large)
    y += 25
    draw.line([(10, y), (390, y)], fill="black", width=2)
    y += 10
    
    # Sale details
    sale_date = sale_data['sale_date']
    if hasattr(sale_date, 'strftime'):
        date_str = sale_date.strftime("%Y-%m-%d %H:%M")
    else:
        date_str = str(sale_date)
    
    draw.text((10, y), f"Sale ID: {sale_data['sales_id']}", fill="black", font=font_normal)
    y += 18
    if sale_data.get('customer_name'):
        draw.text((10, y), f"Customer: {sale_data['customer_name']}", fill="black", font=font_normal)
        y += 18
    draw.text((10, y), f"Date: {date_str}", fill="black", font=font_small)
    y += 18
    draw.line([(10, y), (390, y)], fill="black", width=1)
    y += 10
    
    # Items header
    draw.text((10, y), "Items:", fill="black", font=font_normal)
    y += 18
    
    # Items
    for item in sale_data['items']:
        draw.text((10, y), f"{item['product_name']}", fill="black", font=font_normal)
        y += 16
        draw.text((15, y), f"{item['quantity']} x P{float(item['unit_price']):.2f} = P{float(item['subtotal']):.2f}", fill="black", font=font_small)
        y += 16
    
    draw.line([(10, y), (390, y)], fill="black", width=1)
    y += 10
    
    # Totals
    draw.text((10, y), f"Total: P{float(sale_data['total_amount']):.2f}", fill="black", font=font_normal)
    y += 18
    draw.text((10, y), f"Paid: P{float(sale_data['amount_paid']):.2f}", fill="black", font=font_normal)
    y += 18
    draw.text((10, y), f"Change: P{float(sale_data['change_amount']):.2f}", fill="black", font=font_normal)
    y += 18
    draw.text((10, y), f"Method: {sale_data['payment_method']}", fill="black", font=font_normal)
    y += 18
    if sale_data.get('due_date'):
        sdue_date = sale_data['due_date']
        if hasattr(sdue_date, 'strftime'):
            due_date_str = sdue_date.strftime("%Y-%m-%d")
        else:
            due_date_str = str(sdue_date)
        draw.text((10, y), f"Due Date: {due_date_str}", fill="black", font=font_normal)
        y += 18
    y += 7
    # Footer
    draw.text((170, y), "Thank you!", fill="black", font=font_large)
    
    return img


def save_receipt(sale_id):
    """Save receipt image to file"""
    sale_data = get_sale_data(sale_id)
    if not sale_data:
        return False
    
    try:
        img = generate_receipt(sale_data)
        filename = f"receipt_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(filename)
        return filename
    except Exception as e:
        print(f"Error saving receipt: {e}")
        return False


def get_payment_receipt_data(customer, amount_paid, payment_method="BALANCE PAYMENT", sale_id=None, due_date=None):
    return {
        'sales_id': sale_id or f"PAY-{customer.get('customer_id')}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'sale_date': datetime.now(),
        'customer_name': customer.get('name', 'Walk-in'),
        'total_amount': amount_paid,
        'amount_paid': amount_paid,
        'change_amount': 0.0,
        'payment_method': payment_method,
        'due_date': due_date,
        'items': []
    }


def save_payment_receipt(payment_data):
    try:
        img = generate_receipt(payment_data)
        sale_id = payment_data.get('sales_id')
        filename = f"payment_receipt_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(filename)
        return filename
    except Exception as e:
        print(f"Error saving payment receipt: {e}")
        return False
