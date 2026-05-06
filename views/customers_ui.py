import customtkinter as ctk
from tkinter import ttk, messagebox
from models.customer import *
from models.credit import apply_overdue_charges
from utils.colors import get_color
from utils.receipt import get_payment_receipt_data, generate_receipt, save_payment_receipt


class CustomersScreen:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ctk.CTkFrame(parent, corner_radius=12, fg_color=get_color("bg_primary"))
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Track if we're viewing backup customers
        self.viewing_backup = False

        self.build_ui()
        self.load_customers()

    def build_ui(self):
        header = ctk.CTkLabel(self.frame, text="Customers", font=ctk.CTkFont(size=20, weight="bold"), text_color=get_color("primary"), fg_color="transparent")
        header.pack(pady=12)

        search_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by name, contact, address...", width=320, fg_color=get_color("bg_secondary"), border_color=get_color("border"), text_color=get_color("text_primary"))
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search())

        self.refresh_btn = ctk.CTkButton(search_frame, text="Refresh", width=100, command=self.load_customers, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.refresh_btn.pack(side="left", pady=8)

        columns = ("customer_id", "name", "contact_number", "address", "current_balance")
        self.tree_frame = ctk.CTkFrame(self.frame, fg_color=get_color("bg_secondary"), corner_radius=12)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.customers_tv = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=12)
        headings = {
            "customer_id": "ID",
            "name": "Name",
            "contact_number": "Contact",
            "address": "Address",
            "current_balance": "Balance"
        }
        for col in columns:
            self.customers_tv.heading(col, text=headings[col])
            self.customers_tv.column(col, width=120 if col != "address" else 180, anchor="center")

        self.customers_tv.pack(side="left", fill="both", expand=True)
        self.customers_tv.bind("<<TreeviewSelect>>", self.on_customer_select)

        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.customers_tv.yview)
        self.customers_tv.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")

        actions = ctk.CTkFrame(self.frame, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 10))

        self.add_btn = ctk.CTkButton(actions, text="Add Customer", width=120, command=self.open_add_customer, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.add_btn.pack(side="left", padx=8)

        self.edit_btn = ctk.CTkButton(actions, text="Edit Selected", width=120, command=self.open_edit_customer, state="disabled", fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.edit_btn.pack(side="left", padx=8)

        self.delete_btn = ctk.CTkButton(actions, text="Delete Selected", width=120, command=self.delete_selected_customer, state="disabled", fg_color=get_color("status_error"), hover_color=get_color("status_error_dark"))
        self.delete_btn.pack(side="left", padx=8)

        self.mark_paid_btn = ctk.CTkButton(
            actions,
            text="Mark as Paid",
            width=140,
            command=self.mark_selected_paid,
            state="disabled",
            fg_color=get_color("status_success"),
            hover_color=get_color("status_success_dark")
        )
        self.mark_paid_btn.pack(side="left", padx=8)

        self.deleted_customers_btn = ctk.CTkButton(
            actions,
            text="Deleted Customers",
            width=140,
            command=self.view_deleted_customers,
            fg_color=get_color("status_warning"),
            hover_color=get_color("status_warning_dark")
        )
        self.deleted_customers_btn.pack(side="left", padx=8)

        # View customers button (initially hidden)
        self.view_customers_btn = ctk.CTkButton(
            actions,
            text="View Customers",
            width=140,
            command=self.view_active_customers,
            fg_color=get_color("button_primary"),
            hover_color=get_color("button_primary_dark"),
            state="disabled"
        )

        # Restore from backup button (initially hidden)
        self.restore_btn = ctk.CTkButton(
            actions,
            text="Restore from Backup",
            width=140,
            command=self.restore_selected_customer,
            state="disabled",
            fg_color="#10b981",
            hover_color="#059669"
        )

        # Delete permanently button (initially hidden)
        self.delete_permanently_btn = ctk.CTkButton(
            actions,
            text="Delete Permanently",
            width=140,
            command=self.delete_permanently_selected_customer,
            state="disabled",
            fg_color=get_color("status_error_dark"),
            hover_color="#dc2626"
        )
        self.delete_permanently_btn.pack(side="left", padx=8)

    def _get_customer_display_values(self, customer):
        return (
            customer.get("customer_id"),
            customer.get("name", "") or "",
            customer.get("contact_number", "") or "",
            customer.get("address", "") or "",
            f"₱{float(customer.get('current_balance', 0.0) or 0.0):.2f}"
        )

    def load_customers(self):
        self.customers_tv.delete(*self.customers_tv.get_children())
        
        if self.viewing_backup:
            rows = get_all_backup_customers() or []
        else:
            apply_overdue_charges()
            rows = get_all_customers() or []
        
        for c in rows:
            self.customers_tv.insert("", "end", values=self._get_customer_display_values(c))
        
        self.edit_btn.configure(state="disabled")
        self.delete_btn.configure(state="disabled")
        self.mark_paid_btn.configure(state="disabled")
        
        self.update_button_visibility()

    def on_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.load_customers()
            return

        self.customers_tv.delete(*self.customers_tv.get_children())
        
        if self.viewing_backup:
            rows = search_backup_customer(keyword) or []
        else:
            rows = search_customer(keyword) or []
        
        for c in rows:
            self.customers_tv.insert("", "end", values=self._get_customer_display_values(c))

    def on_customer_select(self, event=None):
        selected = self.customers_tv.selection()
        if selected:
            self.edit_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")
            
            if self.viewing_backup:
                # When viewing backup, enable restore and delete permanently buttons
                self.restore_btn.configure(state="normal")
                self.delete_permanently_btn.configure(state="normal")
                self.mark_paid_btn.configure(state="disabled")
            else:
                # When viewing active customers, check balance for mark paid button
                item = self.customers_tv.item(selected[0])
                customer_id = item["values"][0]
                customer = get_customer_by_id(customer_id)
                if customer and float(customer.get("current_balance", 0) or 0) > 0:
                    self.mark_paid_btn.configure(state="normal")
                else:
                    self.mark_paid_btn.configure(state="disabled")
                self.restore_btn.configure(state="disabled")
        else:
            self.edit_btn.configure(state="disabled")
            self.delete_btn.configure(state="disabled")
            self.mark_paid_btn.configure(state="disabled")
            self.restore_btn.configure(state="disabled")

    def open_add_customer(self):
        self.open_customer_form("Add Customer", customer=None)

    def open_edit_customer(self):
        selected = self.customers_tv.selection()
        if not selected:
            return

        item = self.customers_tv.item(selected[0])
        customer_id = item["values"][0]
        customer = get_customer_by_id(customer_id)
        if not customer:
            messagebox.showwarning("Not found", "Selected customer could not be loaded.")
            return

        self.open_customer_form("Edit Customer", customer)

    def open_customer_form(self, title, customer=None):
        self.form_window = ctk.CTkToplevel(self.frame)
        self.form_window.title(title)
        self.form_window.geometry("420x380")
        self.form_window.resizable(False, False)
        self.form_window.grab_set()

        ctk.CTkLabel(self.form_window, text="Customer Name", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 4))
        name_entry = ctk.CTkEntry(self.form_window, placeholder_text="Customer Name")
        name_entry.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(self.form_window, text="Address", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        address_entry = ctk.CTkEntry(self.form_window, placeholder_text="Address")
        address_entry.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(self.form_window, text="Contact Number", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 4))
        contact_entry = ctk.CTkEntry(self.form_window, placeholder_text="Enter 11-digit contact number")
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

        if customer is not None:
            name_entry.insert(0, customer.get("name", "") or "")
            contact_entry.insert(0, customer.get("contact_number", "") or "")
            address_entry.insert(0, customer.get("address", "") or "")

        def submit_customer():
            name = name_entry.get().strip()
            address = address_entry.get().strip()
            contact = contact_entry.get().strip()

            if not name:
                messagebox.showerror("Missing Information", "Please fill in customer name.")
                return

            # Contact number must be exactly 11 digits if provided
            if contact and len(contact) != 11:
                messagebox.showerror("Invalid Contact Number", "Contact number must be exactly 11 digits.")
                return

            if customer is None:
                add_customer(name, address, contact)
                messagebox.showinfo("Customer Added", f"Customer '{name}' has been added.")
                # Close and refresh
                self.form_window.destroy()
                self.load_customers()
            else:
                update_customer(
                    customer["customer_id"],
                    name=name,
                    address=address,
                    contact_number=contact
                )
                messagebox.showinfo("Customer Updated", f"Customer '{name}' has been updated.")
                # Close and refresh
                self.form_window.destroy()
                self.load_customers()

        save_text = "Add" if customer is None else "Update"
        submit_btn = ctk.CTkButton(self.form_window, text=save_text, fg_color="#16a34a", hover_color="#15803d", command=submit_customer)
        submit_btn.pack(padx=20, pady=(0, 20))


    def delete_selected_customer(self):
        selected = self.customers_tv.selection()
        if not selected:
            return

        item = self.customers_tv.item(selected[0])
        customer_id = item["values"][0]

        if messagebox.askyesno(
            "Confirm Delete",
            "This will delete the customer information in sales history.\n\nDo you want to continue?"
        ):
            from models.customer import delete_customer
            deleted = delete_customer(customer_id)
            if deleted:
                messagebox.showinfo("Removed", "Customer and related sales history deleted successfully.")
            else:
                messagebox.showwarning(
                    "Unable to Delete",
                    "The customer could not be deleted. Please try again or check the database constraints."
                )
            self.load_customers()

    def mark_selected_paid(self):
        selected = self.customers_tv.selection()
        if not selected:
            return

        item = self.customers_tv.item(selected[0])
        customer_id = item["values"][0]
        customer = get_customer_by_id(customer_id)
        if not customer:
            messagebox.showwarning("Not Found", "Selected customer could not be loaded.")
            return

        balance = float(customer.get("current_balance", 0.0) or 0.0)
        if balance <= 0:
            messagebox.showinfo("No Balance", "This customer has no outstanding balance.")
            return

        if not messagebox.askyesno(
            "Confirm Payment",
            f"Mark {customer['name']} as paid?\n\nThis will clear the outstanding balance of ₱{balance:.2f}"
            " and update all unpaid sales to PAID."
        ):
            return

        from models.customer import mark_customer_paid_balance
        payment_sale_id = mark_customer_paid_balance(customer_id)
        if payment_sale_id:
            messagebox.showinfo("Marked Paid", f"{customer['name']}'s balance has been cleared.")
            self.show_payment_receipt(customer, balance, payment_sale_id)
        else:
            messagebox.showerror("Error", "Failed to mark customer as paid.")

        self.load_customers()

    def update_button_visibility(self):
        """Update button visibility based on whether we're viewing backup or active customers"""
        if self.viewing_backup:
            # Hide active customer buttons
            self.add_btn.pack_forget()
            self.edit_btn.pack_forget()
            self.delete_btn.pack_forget()
            self.mark_paid_btn.pack_forget()
            self.deleted_customers_btn.pack_forget()
            
            # Show backup view buttons
            self.view_customers_btn.configure(state="normal")
            self.view_customers_btn.pack(side="left", padx=8)
            self.restore_btn.configure(state="disabled")
            self.restore_btn.pack(side="left", padx=8)
            self.delete_permanently_btn.configure(state="disabled")
            self.delete_permanently_btn.pack(side="left", padx=8)
        else:
            # Show active customer buttons
            if not self.add_btn.winfo_viewable():
                self.add_btn.pack(side="left", padx=8)
            if not self.edit_btn.winfo_viewable():
                self.edit_btn.pack(side="left", padx=8)
            if not self.delete_btn.winfo_viewable():
                self.delete_btn.pack(side="left", padx=8)
            if not self.mark_paid_btn.winfo_viewable():
                self.mark_paid_btn.pack(side="left", padx=8)
            if not self.deleted_customers_btn.winfo_viewable():
                self.deleted_customers_btn.pack(side="left", padx=8)
            
            # Hide backup view buttons
            self.view_customers_btn.pack_forget()
            self.restore_btn.pack_forget()
            self.delete_permanently_btn.pack_forget()

    def view_deleted_customers(self):
        """Switch to viewing backup customers"""
        self.viewing_backup = True
        self.search_entry.delete(0, ctk.END)
        self.load_customers()

    def view_active_customers(self):
        """Switch back to viewing active customers"""
        self.viewing_backup = False
        self.search_entry.delete(0, ctk.END)
        self.load_customers()

    def restore_selected_customer(self):
        """Restore a customer from backup to active customers"""
        selected = self.customers_tv.selection()
        if not selected:
            return

        item = self.customers_tv.item(selected[0])
        customer_id = item["values"][0]
        customer_name = item["values"][1]

        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore '{customer_name}' to active customers?\n\nThis will move the customer from backup back to the active list."
        ):
            if restore_backup_customer(customer_id):
                messagebox.showinfo("Restored", f"Customer '{customer_name}' has been restored to active customers.")
                self.load_customers()
            else:
                messagebox.showerror("Error", "Failed to restore customer from backup.")

    def delete_permanently_selected_customer(self):
        """Permanently delete a customer from backup"""
        selected = self.customers_tv.selection()
        if not selected:
            return

        item = self.customers_tv.item(selected[0])
        customer_id = item["values"][0]
        customer_name = item["values"][1]

        if messagebox.askyesno(
            "Confirm Permanent Delete",
            f"Permanently delete '{customer_name}'?\n\nWARNING: This action cannot be undone. The customer will be deleted from backup permanently."
        ):
            from models.customer import delete_backup_customer_permanently
            if delete_backup_customer_permanently(customer_id):
                messagebox.showinfo("Deleted", f"Customer '{customer_name}' has been permanently deleted.")
                self.load_customers()
            else:
                messagebox.showerror("Error", "Failed to permanently delete customer.")



    def show_payment_receipt(self, customer, amount_paid, payment_sale_id=None):
        receipt_window = ctk.CTkToplevel(self.frame)
        receipt_window.title("Payment Receipt")
        receipt_window.geometry("500x700")
        receipt_window.grab_set()

        try:
            payment_data = get_payment_receipt_data(customer, amount_paid, sale_id=payment_sale_id)
            receipt_img = generate_receipt(payment_data)
            ctk_image = ctk.CTkImage(light_image=receipt_img, dark_image=receipt_img, size=(receipt_img.width, receipt_img.height))

            img_label = ctk.CTkLabel(receipt_window, image=ctk_image, text="")
            img_label.image = ctk_image
            img_label.pack(padx=10, pady=10, fill="both", expand=True)

            btn_frame = ctk.CTkFrame(receipt_window)
            btn_frame.pack(fill="x", padx=10, pady=10)

            def save_receipt_file():
                filename = save_payment_receipt(payment_data)
                if filename:
                    messagebox.showinfo("Success", f"Receipt saved as:\n{filename}")
                else:
                    messagebox.showerror("Error", "Failed to save receipt")

            save_btn = ctk.CTkButton(
                btn_frame,
                text="Save Receipt",
                fg_color="#27c260",
                hover_color="#1a6937",
                command=save_receipt_file
            )
            save_btn.pack(side="left", padx=5)

            close_btn = ctk.CTkButton(
                btn_frame,
                text="Close",
                fg_color="#6b7280",
                hover_color="#4b5563",
                command=receipt_window.destroy
            )
            close_btn.pack(side="left", padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Error generating receipt: {str(e)}")
            receipt_window.destroy()
