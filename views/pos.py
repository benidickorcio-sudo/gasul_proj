import customtkinter as ctk
from tkinter import ttk, messagebox
from models.product import view_products, get_product_by_id
from models.restock import get_latest_unit_cost
from models.sales import create_sale, log_transaction
from models.customer import get_all_customers, add_customer
from utils.receipt import get_sale_data, generate_receipt, save_receipt
from utils.auth import get_current_user
from utils.colors import get_color
from database import get_connection
from datetime import datetime, timedelta

CREDIT_DUE_DAYS = 7


class POSScreen:
    def __init__(self, parent, on_checkout=None):
        self.parent = parent
        self.on_checkout = on_checkout
        self.frame = ctk.CTkFrame(parent, corner_radius=12, fg_color=get_color("bg_primary"))
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.products = []
        self.cart_items = []

        self.build_ui()

    def build_ui(self):
        # Header
        self.header_label = ctk.CTkLabel(
            self.frame,
            text="Point of Sales",
            text_color=get_color("primary"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.header_label.pack(pady=(10, 10))

        top_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Search product...", width=320, fg_color=get_color("bg_secondary"), border_color=get_color("border"), text_color=get_color("text_primary"))
        self.search_entry.pack(side="left", padx=(10, 8), pady=10)
        self.search_entry.bind("<Return>", lambda e: self.load_products())
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_products())

        self.refresh_customers()

        tables_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        tables_frame.pack(fill="both", expand=True, padx=10, pady=(8, 12))

        product_frame = ctk.CTkFrame(tables_frame, fg_color=get_color("bg_secondary"), corner_radius=12)
        product_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=2)

        cart_frame = ctk.CTkFrame(tables_frame, fg_color=get_color("bg_secondary"), corner_radius=12)
        cart_frame.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=2)

        self.products_header = ctk.CTkLabel(product_frame, text="PRODUCTS", font=ctk.CTkFont(size=16, weight="bold"), text_color=get_color("primary"), fg_color="transparent")
        self.products_header.pack(anchor="w", padx=10, pady=(5, 4))

        product_action_frame = ctk.CTkFrame(product_frame, fg_color="transparent")
        product_action_frame.pack(fill="x", padx=5, pady=(0, 8))

        self.quantity_entry = ctk.CTkEntry(product_action_frame, placeholder_text="Quantity", width=100, fg_color=get_color("bg_primary"), border_color=get_color("border"), text_color=get_color("text_primary"))
        self.quantity_entry.pack(side="left",padx=8,pady=8)

        self.add_btn = ctk.CTkButton(product_action_frame, text="Add to Cart", command=self.add_selected_to_cart, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.add_btn.pack(side="left")

        self.products_tv = ttk.Treeview(product_frame, columns=("id","name","price","qty"), show="headings", height=8)
        for col, txt in [("id","ID"),("name","Name"),("price","Price"),("qty","Stock")]:
            self.products_tv.heading(col, text=txt, command=lambda c=col: self.sort_products(c, False))
            self.products_tv.column(col, width=120, anchor="center")
        self.products_tv.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        self.cart_header = ctk.CTkLabel(cart_frame, text="CART", font=ctk.CTkFont(size=16, weight="bold"), text_color=get_color("primary"), fg_color="transparent")
        self.cart_header.pack(anchor="w", padx=10, pady=(5, 4))

        cart_action_frame = ctk.CTkFrame(cart_frame, fg_color="transparent")
        cart_action_frame.pack(fill="x", padx=5, pady=(0, 8))

        self.decrease_btn = ctk.CTkButton(cart_action_frame, text="Decrease Qty", command=self.decrease_selected_quantity, fg_color=get_color("status_warning"), hover_color=get_color("status_warning_dark"))
        self.decrease_btn.pack(side="left",padx=8,pady=8)

        self.remove_btn = ctk.CTkButton(cart_action_frame, text="Remove Selected", command=self.remove_selected_from_cart, fg_color=get_color("status_error"), hover_color=get_color("status_error_dark"))
        self.remove_btn.pack(side="left",padx=8,pady=8)

        self.total_label = ctk.CTkLabel(cart_action_frame, text="Total: ₱0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=get_color("accent_blue"))
        self.total_label.pack(side="right", padx=(0, 10))

        self.cart_tv = ttk.Treeview(cart_frame, columns=("prod","qty","unit","subtotal"), show="headings", height=8)
        for col, txt in [("prod","Product"),("qty","QTY"),("unit","Unit"),("subtotal","Subtotal")]:
            self.cart_tv.heading(col, text=txt)
            self.cart_tv.column(col, width=120, anchor="center")
        self.cart_tv.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        # Checkout and add-customer buttons between tables
        checkout_container = ctk.CTkFrame(self.frame,bg_color="transparent", fg_color="transparent")
        checkout_container.pack(fill="x", padx=10, pady=(10, 10))

        self.add_customer_btn = ctk.CTkButton(
            checkout_container,
            text="Add customer",
            fg_color=get_color("accent_pink"),
            hover_color="#ec4899",
            command=self.show_add_customer_dialog,
            height=40,
            width=140,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.add_customer_btn.pack(side="left", padx=(250,475), pady=15)

        self.checkout_btn = ctk.CTkButton(
            checkout_container,
            text="Checkout",
            fg_color=get_color("button_primary"),
            hover_color=get_color("button_primary_dark"),
            command=self.show_checkout_dialog,
            height=40,
            width=140,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.checkout_btn.pack(side="left", pady=15)

        self.status_label = ctk.CTkLabel(self.frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_label.pack(pady=10)

        self.load_products()

    def load_products(self):
        keyword = self.search_entry.get().strip().lower()
        self.products = view_products() or []
        self.products_tv.delete(*self.products_tv.get_children())
        for p in self.products:
            if not keyword or keyword in p["name"].lower():
                latest_cost = get_latest_unit_cost(p["product_id"]) or float(p.get("cost_price", 0.0))
                profit = float(p.get("profit", 0.0))
                price_value = latest_cost + profit if latest_cost > 0 else p.get("total_price", p.get("price", 0.0))
                self.products_tv.insert("", "end", values=(p["product_id"], p["name"], f"{price_value:.2f}", p["quantity"]))
        self.refresh_cart_prices()

    def refresh_cart_prices(self):
        if not self.cart_items:
            return

        updated = False
        for item in self.cart_items:
            product = get_product_by_id(item["product_id"])
            if not product:
                continue
            latest_cost = get_latest_unit_cost(product["product_id"]) or float(product.get("cost_price", 0.0))
            profit = float(product.get("profit", 0.0))
            current_price = latest_cost + profit if latest_cost > 0 else product.get("total_price", product.get("price", 0.0))
            if item["unit_price"] != current_price:
                item["unit_price"] = current_price
                item["subtotal"] = item["quantity"] * current_price
                updated = True

        if updated:
            self.update_cart_view()

    def sort_products(self, col, reverse=False):
        def parse(value):
            try:
                return float(str(value).replace("₱", ""))
            except Exception:
                return value

        data = [(self.products_tv.set(child, col), child) for child in self.products_tv.get_children("")]
        data.sort(key=lambda t: parse(t[0]), reverse=reverse)
        for index, (_, item) in enumerate(data):
            self.products_tv.move(item, "", index)

        self.products_tv.heading(col, command=lambda: self.sort_products(col, not reverse))

    def add_to_cart(self, product, quantity):
        qty = int(quantity)
        if qty <= 0:
            messagebox.showwarning("Invalid Quantity", "Quantity must be greater than 0.")
            return False
        if qty > product["quantity"]:
            messagebox.showwarning(
                "Insufficient Stock",
                f"Cannot add {qty} units. Only {product['quantity']} units of '{product['name']}' available in inventory."
            )
            return False

        latest_cost = get_latest_unit_cost(product["product_id"]) or float(product.get("cost_price", 0.0))
        profit = float(product.get("profit", 0.0))
        unit_price = latest_cost + profit if latest_cost > 0 else product.get("total_price", product.get("price", 0.0))
        existing = next((x for x in self.cart_items if x["product_id"] == product["product_id"]), None)
        if existing:
            existing["quantity"] += qty
            existing["unit_price"] = unit_price
            existing["subtotal"] = existing["quantity"] * unit_price
        else:
            self.cart_items.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": qty * unit_price,
            })

        self.update_cart_view()
        return True

    def add_selected_to_cart(self):
        selected = self.products_tv.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product first.")
            return

        item = self.products_tv.item(selected[0])["values"]
        product = get_product_by_id(int(item[0]))
        q = self.quantity_entry.get().strip() or "1"

        if not q.isdigit() or int(q) <= 0:
            messagebox.showwarning("Invalid Quantity", "Please enter a valid quantity greater than 0.")
            return

        if self.add_to_cart(product, int(q)):
            self.quantity_entry.delete(0, ctk.END)
            self.status_label.configure(text=f"Added {q} x {product['name']} to cart", text_color=get_color("status_success"))

    def decrease_selected_quantity(self):
        selected = self.cart_tv.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a cart item to decrease quantity.")
            return
        item = self.cart_tv.item(selected[0])["values"]
        prod_name = item[0]
        cart_item = next((x for x in self.cart_items if x["name"] == prod_name), None)
        if cart_item:
            if cart_item["quantity"] > 1:
                cart_item["quantity"] -= 1
                cart_item["subtotal"] = cart_item["quantity"] * cart_item["unit_price"]
                self.status_label.configure(text=f"Decreased {prod_name} quantity to {cart_item['quantity']}", text_color=get_color("status_success"))
            else:
                self.cart_items = [x for x in self.cart_items if x["name"] != prod_name]
                self.status_label.configure(text=f"Removed {prod_name} from cart", text_color=get_color("status_success"))
            self.update_cart_view()

    def remove_selected_from_cart(self):
        selected = self.cart_tv.selection()
        if not selected:
            return
        item = self.cart_tv.item(selected[0])["values"]
        prod_name = item[0]
        self.cart_items = [x for x in self.cart_items if x["name"] != prod_name]
        self.update_cart_view()

    def update_cart_view(self):
        self.cart_tv.delete(*self.cart_tv.get_children())
        total = 0
        for item in self.cart_items:
            self.cart_tv.insert("", "end", values=(item["name"], item["quantity"], f"₱{item['unit_price']:.2f}", f"₱{item['subtotal']:.2f}"))
            total += item["subtotal"]
        self.total_label.configure(text=f"Total: ₱{total:.2f}")

    def show_checkout_dialog(self):
        if not self.customer_options:
            # Log no customers attempt
            current_user = get_current_user()
            user = current_user.get("username") if current_user else "Unknown"
            log_transaction(None, user, "FAILED", "No customers available: Cannot proceed with checkout.")
            self.status_label.configure(text="No customers available", text_color=get_color("status_error"))
            messagebox.showwarning("Warning", "No customers available. Please add a customer first.")
            return

        total = float(sum(item["subtotal"] for item in self.cart_items)) if self.cart_items else 0.0

        checkout_dialog = ctk.CTkToplevel(self.frame)
        checkout_dialog.title("Checkout")
        checkout_dialog.geometry("420x380")
        checkout_dialog.resizable(False, False)
        checkout_dialog.grab_set()

        ctk.CTkLabel(checkout_dialog, text="Customer", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 4))
        customer_var = ctk.StringVar(value=self.customer_options[0])
        customer_menu = ctk.CTkOptionMenu(checkout_dialog, values=self.customer_options, variable=customer_var)
        customer_menu.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(checkout_dialog, text="Payment Method", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        payment_method_var = ctk.StringVar(value="CASH")
        payment_menu = ctk.CTkOptionMenu(checkout_dialog, values=["CASH", "GCASH", "CREDIT", "PAY BALANCE", "OTHER"], variable=payment_method_var)
        payment_menu.pack(fill="x", padx=20, pady=(0, 12))

        # Frame for custom payment method
        custom_payment_frame = ctk.CTkFrame(checkout_dialog, fg_color="transparent")
        custom_payment_frame.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(custom_payment_frame, text="Custom Payment Method", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 4))
        custom_payment_entry = ctk.CTkEntry(custom_payment_frame, placeholder_text="Enter payment method")
        custom_payment_entry.pack(fill="x")

        # Initially hide the custom payment frame
        custom_payment_frame.pack_forget()

        def on_payment_method_change(*args):
            if payment_method_var.get() == "OTHER":
                custom_payment_frame.pack(fill="x", padx=20, pady=(0, 12))
            else:
                custom_payment_frame.pack_forget()

        payment_method_var.trace("w", on_payment_method_change)

        ctk.CTkLabel(checkout_dialog, text="Amount Paid", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        amount_paid_entry = ctk.CTkEntry(checkout_dialog, placeholder_text="0.00")
        amount_paid_entry.pack(fill="x", padx=20, pady=(0, 12))

        def submit_checkout():
            payment_method = payment_method_var.get().strip().upper()
            
            # Handle OTHER payment method
            if payment_method == "OTHER":
                custom_payment = custom_payment_entry.get().strip()
                if not custom_payment:
                    # Log missing custom payment method
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", "Missing Information: Custom payment method is required.")
                    messagebox.showerror("Missing Information", "Please enter a custom payment method.")
                    return
                payment_method = custom_payment.upper()
            
            if not self.cart_items and payment_method != "PAY BALANCE":
                # Log empty cart attempt
                current_user = get_current_user()
                user = current_user.get("username") if current_user else "Unknown"
                log_transaction(None, user, "FAILED", "Cart is empty: No items to checkout.")
                messagebox.showerror("Cart is empty", "Please add items to cart or select PAY BALANCE.")
                return
            
            customer_name = customer_var.get().strip()
            customer_id = self.customer_map.get(customer_name)
            
            # Handle PAY BALANCE payment method
            if payment_method == "PAY BALANCE":
                if not customer_id:
                    # Log invalid customer attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", "Invalid Customer: Walk-in customers cannot pay balance.")
                    messagebox.showerror("Invalid Customer", "Please select a registered customer to pay balance.")
                    return
                
                customer_balance = get_customer_balance(customer_id)
                if customer_balance <= 0:
                    # Log no balance attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", f"No Balance: Customer {customer_name} has no outstanding balance.")
                    messagebox.showerror("No Balance", f"Customer {customer_name} has no outstanding balance to pay.")
                    return
                
                if not amount_paid_text or not amount_paid_text.replace('.', '', 1).isdigit():
                    # Log invalid payment attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", "Invalid Payment: Enter a valid amount paid.")
                    messagebox.showerror("Invalid Payment", "Enter a valid amount paid.")
                    return
                amount_paid = float(amount_paid_text)
                
                if amount_paid > customer_balance:
                    # Log overpayment attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", f"Overpayment: Amount paid (₱{amount_paid:.2f}) exceeds balance (₱{customer_balance:.2f}).")
                    messagebox.showerror("Overpayment", f"Amount paid (₱{amount_paid:.2f}) cannot exceed the outstanding balance (₱{customer_balance:.2f}).")
                    return
                
                # Confirm payment
                if not messagebox.askyesno("Confirm Balance Payment", f"Pay ₱{amount_paid:.2f} towards {customer_name}'s balance of ₱{customer_balance:.2f}?"):
                    return
                
                # Update customer balance
                new_balance = customer_balance - amount_paid
                update_customer(customer_id, current_balance=new_balance)
                
                # Create a balance payment sale
                try:
                    sale_id = create_sale(customer_id, [], "BALANCE PAYMENT", amount_paid, amount_paid, amount_paid)
                except Exception as e:
                    # Log failed transaction
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", str(e))
                    messagebox.showerror("Transaction Error", f"Error processing balance payment: {str(e)}")
                    return
                
                messagebox.showinfo("Balance Payment", f"Balance payment of ₱{amount_paid:.2f} processed for {customer_name}.\nNew balance: ₱{new_balance:.2f}\nSale ID: {sale_id}")
                checkout_dialog.destroy()
                self.status_label.configure(text=f"Balance payment completed: {sale_id}", text_color=get_color("status_success"))
                return
            
            amount_paid_text = amount_paid_entry.get().strip()
            amount_paid = 0.0

            if payment_method == "CREDIT":
                if not customer_id:
                    # Log invalid customer attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", "Invalid Customer: Walk-in customers cannot use credit.")
                    messagebox.showerror("Invalid Customer", "Please select a registered customer for CREDIT purchases. Walk-in customers cannot use credit.")
                    return
                
                if not amount_paid_text:
                    amount_paid = 0.0
                else:
                    if not amount_paid_text.replace('.', '', 1).isdigit():
                        # Log invalid payment attempt
                        current_user = get_current_user()
                        user = current_user.get("username") if current_user else "Unknown"
                        log_transaction(None, user, "FAILED", "Invalid Payment: Enter a valid amount paid.")
                        messagebox.showerror("Invalid Payment", "Enter a valid amount paid.")
                        return
                    amount_paid = float(amount_paid_text)
                
                # Validate that credit payment is less than total (partial payment only)
                if amount_paid >= total:
                    # Log invalid credit payment attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", f"Invalid Credit Payment: Amount paid (₱{amount_paid:.2f}) is equal to or greater than total (₱{total:.2f}). Credit payment should be partial payment only.")
                    messagebox.showinfo("Invalid Credit Payment", f"The downpayment (₱{amount_paid:.2f}) is equal to or greater than the total amount (₱{total:.2f}).\n\nPlease change the payment method to CASH for full payment.")
                    return
                
                # For CREDIT: partial payment only - carry balance to customer account
                balance_due = total - amount_paid
                due_date = datetime.now() + timedelta(days=CREDIT_DUE_DAYS)
                due_date_str = due_date.strftime("%Y-%m-%d")
                if balance_due > 0:
                    confirm_msg = f"""CREDIT PAYMENT DETAILS

Total Purchase: ₱{total:.2f}
Amount Paid Now: ₱{amount_paid:.2f}
Balance Due: ₱{balance_due:.2f}
Due Date: {due_date_str}

This balance of ₱{balance_due:.2f} will be added to {customer_name}'s credit account.

Do you want to proceed?"""
                    if not messagebox.askyesno("Confirm Credit Purchase", confirm_msg):
                        return
                elif balance_due < 0:
                    # Customer overpaid on credit
                    confirm_msg = f"""CREDIT PAYMENT WITH OVERPAYMENT

Total Purchase: ₱{total:.2f}
Amount Paid: ₱{amount_paid:.2f}
Overpayment: ₱{abs(balance_due):.2f}

The overpayment will reduce {customer_name}'s credit balance.

Do you want to proceed?"""
                    if not messagebox.askyesno("Confirm Credit Purchase", confirm_msg):
                        return
            else:
                if not amount_paid_text or not amount_paid_text.replace('.', '', 1).isdigit():
                    # Log invalid payment attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", "Invalid Payment: Enter a valid amount paid.")
                    messagebox.showerror("Invalid Payment", "Enter a valid amount paid.")
                    return
                amount_paid = float(amount_paid_text)
                if amount_paid < total:
                    # Log insufficient payment attempt
                    current_user = get_current_user()
                    user = current_user.get("username") if current_user else "Unknown"
                    log_transaction(None, user, "FAILED", f"Insufficient Payment: Amount paid (₱{amount_paid:.2f}) is less than total (₱{total:.2f}).")
                    messagebox.showerror("Insufficient Payment", "Amount paid must be equal or greater than total.")
                    return
                
                # For CASH: Calculate change to show customer
                change_value = amount_paid - total

            sale_items = [
                {
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "subtotal": item["subtotal"],
                }
                for item in self.cart_items
            ]

            # For CASH/GCASH/OTHER payments, save only the total amount needed in database
            # For CREDIT payments, save the actual amount paid (for partial payment tracking)
            amount_to_save = amount_paid if payment_method == "CREDIT" else total
            
            # For non-CREDIT methods: pass the actual amount received to calculate change properly
            actual_received = amount_paid if payment_method != "CREDIT" else None
            
            try:
                sale_id = create_sale(customer_id, sale_items, payment_method, amount_to_save, total, actual_received, due_date=(due_date if payment_method == "CREDIT" else None))
            except Exception as e:
                # Log failed transaction from POS
                current_user = get_current_user()
                user = current_user.get("username") if current_user else "Unknown"
                log_transaction(None, user, "FAILED", str(e))
                messagebox.showerror("Transaction Error", f"Error processing sale: {str(e)}")
                return

            change_value = 0.0
            try:
                if payment_method == "CREDIT":
                    balance_due = total - amount_paid
                    if balance_due != 0:
                        balance_text = f"Balance Due: ₱{abs(balance_due):.2f}" if balance_due > 0 else f"Extra Payment (Credit): ₱{abs(balance_due):.2f}"
                        if 'due_date_str' in locals():
                            balance_text += f"\nDue Date: {due_date_str}"
                        messagebox.showinfo("CREDIT SALE", f"Sale ID: {sale_id}\nTotal: ₱{total:.2f}\nAmount Paid: ₱{amount_paid:.2f}\n{balance_text}")
                    else:
                        messagebox.showinfo("CREDIT SALE", f"Sale ID: {sale_id}\nTotal: ₱{total:.2f}\nFull Payment Received")
                else:
                    # For CASH/OTHER methods: Show change if overpaid
                    change_value = amount_paid - total
                    if change_value > 0:
                        messagebox.showinfo(f"{payment_method} SALE", f"Sale ID: {sale_id}\nTotal: ₱{total:.2f}\nAmount Paid: ₱{amount_paid:.2f}\nChange: ₱{change_value:.2f}")
                    else:
                        messagebox.showinfo(f"{payment_method} SALE", f"Sale ID: {sale_id}\nTotal: ₱{total:.2f}\nPayment Complete")
                
                checkout_dialog.destroy()
                self.show_receipt(sale_id)
                self.status_label.configure(text=f"Sale completed: {sale_id}", text_color=get_color("status_success"))
                if self.on_checkout:
                    self.on_checkout(sale_id)
                self.clear_cart()
                self.load_products()  # Auto-refresh products table after checkout
            except Exception as e:
                # Log failed transaction from POS
                current_user = get_current_user()
                user = current_user.get("username") if current_user else "Unknown"
                log_transaction(None, user, "FAILED", str(e))
                messagebox.showerror("Error", f"Error completing transaction: {str(e)}")
                checkout_dialog.destroy()

        submit_btn = ctk.CTkButton(checkout_dialog, text="Submit", fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"), command=submit_checkout)
        submit_btn.pack(fill="x", padx=20, pady=(10, 20))

    def show_add_customer_dialog(self):
        dialog = ctk.CTkToplevel(self.frame)
        dialog.title("Add Customer")
        dialog.geometry("420x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Customer Name", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 4))
        name_entry = ctk.CTkEntry(dialog, placeholder_text="Customer Name")
        name_entry.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(dialog, text="Address", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        address_entry = ctk.CTkEntry(dialog, placeholder_text="Address")
        address_entry.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(dialog, text="Contact Number", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        contact_entry = ctk.CTkEntry(dialog, placeholder_text="Enter 11-digit contact number")
        contact_entry.pack(fill="x", padx=20, pady=(0, 16))

        # Real-time validation to prevent non-digit characters from being entered
        def on_key_press(event):
            # Allow control keys: backspace, delete, arrow keys, home, end, tab, etc.
            if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End', 'Tab'):
                return
            # Reject non-digit characters immediately
            if not event.char.isdigit():
                return 'break'
            # Reject if already at 11 digits
            if len(contact_entry.get()) >= 11:
                return 'break'

        # Validation function to clean any pasted non-digit content and enforce 11-digit limit
        def validate_contact(*args):
            current_value = contact_entry.get()
            filtered_value = ''.join(c for c in current_value if c.isdigit())[:11]
            if current_value != filtered_value:
                contact_entry.delete(0, ctk.END)
                contact_entry.insert(0, filtered_value)

        contact_entry.bind("<KeyPress>", on_key_press)
        contact_entry.bind("<KeyRelease>", validate_contact)

        def submit_customer():
            name = name_entry.get().strip()
            address = address_entry.get().strip()
            contact = contact_entry.get().strip()

            if not name or not address:
                # Log failed customer creation attempt
                current_user = get_current_user()
                user = current_user.get("username") if current_user else "Unknown"
                log_transaction(None, user, "FAILED", "Missing Information: Customer name and address are required.")
                messagebox.showerror("Missing Information", "Please fill in customer name and address.")
                return

            # Contact number must be exactly 11 digits if provided
            if contact and len(contact) != 11:
                # Log invalid contact attempt
                current_user = get_current_user()
                user = current_user.get("username") if current_user else "Unknown"
                log_transaction(None, user, "FAILED", f"Invalid Contact Number: Must be exactly 11 digits, got {len(contact)} digits.")
                messagebox.showerror("Invalid Contact Number", "Contact number must be exactly 11 digits.")
                return

            add_customer(name, address, contact)
            self.refresh_customers()
            messagebox.showinfo("Customer Added", f"Customer '{name}' has been added.")
            dialog.destroy()

        submit_btn = ctk.CTkButton(dialog, text="Submit", fg_color=get_color("status_success"), hover_color="#15803d", command=submit_customer)
        submit_btn.pack( padx=20, pady=(0, 20))

    def refresh_customers(self):
        self.customers = get_all_customers()
        self.customer_map = {c["name"]: c["customer_id"] for c in self.customers}
        self.customer_options = [c["name"] for c in self.customers]

    def clear_cart(self):
        self.cart_items = []
        self.update_cart_view()

    def show_receipt(self, sale_id):
        receipt_window = ctk.CTkToplevel(self.frame)
        receipt_window.title(f"Receipt - Sale #{sale_id}")
        receipt_window.geometry("500x700")
        receipt_window.grab_set()
        
        try:
            # Fetch sale data
            sale_data = get_sale_data(sale_id)
            if not sale_data:
                messagebox.showerror("Error", "Could not fetch receipt data")
                receipt_window.destroy()
                return
            
            # Generate receipt image
            receipt_img = generate_receipt(sale_data)
            
            # Convert PIL image to CTkImage for display
            ctk_image = ctk.CTkImage(light_image=receipt_img, dark_image=receipt_img, size=(receipt_img.width, receipt_img.height))
            
            # Display receipt image
            img_label = ctk.CTkLabel(receipt_window, image=ctk_image, text="")
            img_label.image = ctk_image  # Keep a reference
            img_label.pack(padx=10, pady=10, fill="both", expand=True)
            
            # Buttons frame
            btn_frame = ctk.CTkFrame(receipt_window)
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            def save_receipt_file():
                filename = save_receipt(sale_id)
                if filename:
                    messagebox.showinfo("Success", f"Receipt saved as:\n{filename}")
                else:
                    messagebox.showerror("Error", "Failed to save receipt")
            
            save_btn = ctk.CTkButton(
                btn_frame,
                text="Save Receipt",
                fg_color=get_color("status_success"),
                hover_color="#15803d",
                command=save_receipt_file
            )
            save_btn.pack(side="left", padx=5)
            
            close_btn = ctk.CTkButton(
                btn_frame,
                text="Close",
                fg_color=get_color("button_secondary_dark"),
                hover_color=get_color("button_hover_secondary"),
                command=receipt_window.destroy
            )
            close_btn.pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating receipt: {str(e)}")
            receipt_window.destroy()
        
    def _print_receipt(self):
        self.status_label.configure(text="Receipt printed (demo mode).", text_color=get_color("status_success"))

