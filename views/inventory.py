# stock monitoring & restock management - combined view
import customtkinter as ctk
from decimal import Decimal, InvalidOperation
from models.product import view_products, add_product, update_product, delete_product, get_product_by_id, get_total_inventory_value
from models.restock import restock_product, get_all_restock, get_total_restock_cost, get_restock_by_id, update_restock, delete_restock, get_latest_unit_cost
from database import get_connection
from tkinter import messagebox, ttk, simpledialog
from utils.colors import get_color

class InventoryAndRestockScreen():
    def __init__(self, parent, on_update=None):
        self.parent = parent
        self.on_update = on_update
        self.selected_product = None
        self.selected_restock = None
        self.build_ui()
        self.load_inventory()
        self.load_restock_history()

    def _notify_update(self):
        if callable(self.on_update):
            try:
                self.on_update()
            except Exception as e:
                print(f"Error refreshing linked views after inventory change: {e}")

    def build_ui(self):
        # Title
        self.title_label = ctk.CTkLabel(self.parent, text="Inventory Management", font=ctk.CTkFont(size=20, weight="bold"), text_color=get_color("primary"), fg_color="transparent")
        self.title_label.pack(pady=5)

        # Main container with two sides
        main_container = ctk.CTkFrame(self.parent, corner_radius=0, fg_color=get_color("bg_primary"))
        main_container.pack(fill="both", expand=True, padx=(8,9), pady=(15,10))

        # LEFT SIDE - INVENTORY
        inventory_frame = ctk.CTkFrame(main_container, corner_radius=12, fg_color=get_color("bg_primary"))
        inventory_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        inventory_title = ctk.CTkLabel(inventory_frame, text="PRODUCTS", font=ctk.CTkFont(size=16, weight="bold"), text_color=get_color("primary"), fg_color="transparent")
        inventory_title.pack(anchor="center", pady=5)

        inventory_btn_frame = ctk.CTkFrame(inventory_frame, corner_radius=0, fg_color="transparent")
        inventory_btn_frame.configure(fg_color=get_color("bg_primary"))
        inventory_btn_frame.pack(fill="x", padx=3, pady=(0, 3))

        self.add_btn = ctk.CTkButton(inventory_btn_frame, text="Add", command=self.add_product, width=100, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.add_btn.pack(side="left", padx=2, pady=3)

        self.update_btn = ctk.CTkButton(inventory_btn_frame, text="Update", command=self.update_product, width=100, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.update_btn.pack(side="left", padx=2, pady=3)

        self.delete_btn = ctk.CTkButton(inventory_btn_frame, text="Delete", fg_color=get_color("status_error"), command=self.delete_product, width=100, hover_color=get_color("status_error_dark"))
        self.delete_btn.pack(side="left", padx=2, pady=3)

        self.tree_frame = ctk.CTkFrame(inventory_frame, corner_radius=0, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Name", "Cost Price", "Quantity", "Profit", "Total Price", "Status"), show="headings", height=2)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Cost Price", text="Cost Price")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Profit", text="Profit")
        self.tree.heading("Total Price", text="Total Price")
        self.tree.heading("Status", text="Status")

        self.tree.column("ID", width=70, anchor="center", stretch=True)
        self.tree.column("Name", width=180, anchor="center", stretch=True)
        self.tree.column("Cost Price", width=95, anchor="center", stretch=True)
        self.tree.column("Quantity", width=90, anchor="center", stretch=True)
        self.tree.column("Profit", width=85, anchor="center", stretch=True)
        self.tree.column("Total Price", width=95, anchor="center", stretch=True)
        self.tree.column("Status", width=90, anchor="center", stretch=True)

        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        self.vsb.pack(side="right", fill="y", padx=(0, 2), pady=2)

        # Total stock amount label frame
        total_frame = ctk.CTkFrame(inventory_frame, corner_radius=8, fg_color=get_color("bg_primary"))
        
        total_frame.pack(fill="x", padx=3, pady=(8, 0))

        self.total_stock_label = ctk.CTkLabel(
            total_frame,
            text="Total Inventory Value: ₱0.00",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=get_color("primary")
        )
        self.total_stock_label.pack(anchor="e", padx=12, pady=8)

        # RIGHT SIDE - RESTOCK
        restock_frame = ctk.CTkFrame(main_container, corner_radius=0)
        restock_frame.configure(fg_color=get_color("bg_primary"))
        restock_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        restock_title = ctk.CTkLabel(restock_frame, text="RESTOCK HISTORY", font=ctk.CTkFont(size=16, weight="bold"),fg_color="transparent", text_color=get_color("primary"))
        restock_title.pack(anchor="center", padx=3, pady=(0, 3))

        restock_btn_frame = ctk.CTkFrame(restock_frame, corner_radius=0)
        restock_btn_frame.configure(fg_color=get_color("bg_primary"))
        restock_btn_frame.pack(fill="x", pady=5,padx=3)

        self.add_restock_btn = ctk.CTkButton(restock_btn_frame, text="Restock Product", command=self.add_restock, width=120)
        self.add_restock_btn.pack(side="left", padx=2, pady=3)

        self.update_restock_btn = ctk.CTkButton(restock_btn_frame, text="Update", command=self.update_restock, width=80)
        self.update_restock_btn.pack(side="left", padx=2, pady=3)

        self.delete_restock_btn = ctk.CTkButton(restock_btn_frame, text="Delete", fg_color=get_color("status_error"), command=self.delete_restock, width=80)
        self.delete_restock_btn.pack(side="left", padx=2, pady=3)

        self.refresh_restock_btn = ctk.CTkButton(restock_btn_frame, text="Refresh", command=self.load_restock_history, width=100, fg_color=get_color("button_primary"), hover_color=get_color("button_primary_dark"))
        self.refresh_restock_btn.pack(side="left", padx=2, pady=3)

        restock_tree_frame = ctk.CTkFrame(restock_frame, corner_radius=0, fg_color="transparent")
        restock_tree_frame.pack(fill="both", expand=True)

        self.restock_tree = ttk.Treeview(restock_tree_frame, columns=("ID", "Product", "Quantity", "Unit Cost", "Total Cost", "Date"), show="headings", height=2)
        self.restock_tree.heading("ID", text="ID")
        self.restock_tree.heading("Product", text="Product")
        self.restock_tree.heading("Quantity", text="Quantity")
        self.restock_tree.heading("Unit Cost", text="Unit Cost")
        self.restock_tree.heading("Total Cost", text="Total Cost")
        self.restock_tree.heading("Date", text="Date")

        self.restock_tree.column("ID", width=70, anchor="center", stretch=True)
        self.restock_tree.column("Product", width=180, anchor="center", stretch=True)
        self.restock_tree.column("Quantity", width=90, anchor="center", stretch=True)
        self.restock_tree.column("Unit Cost", width=100, anchor="center", stretch=True)
        self.restock_tree.column("Total Cost", width=100, anchor="center", stretch=True)
        self.restock_tree.column("Date", width=120, anchor="center", stretch=True)

        restock_vsb = ttk.Scrollbar(restock_tree_frame, orient="vertical", command=self.restock_tree.yview)
        self.restock_tree.configure(yscrollcommand=restock_vsb.set)

        self.restock_tree.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        restock_vsb.pack(side="right", fill="y", padx=(0, 2), pady=2)

        # Total restock cost label frame
        total_restock_frame = ctk.CTkFrame(restock_frame, corner_radius=8, fg_color=get_color("bg_primary"))
        total_restock_frame.pack(fill="x", padx=3, pady=(8, 0))

        self.total_restock_label = ctk.CTkLabel(
            total_restock_frame,
            text="Total Restock Cost: ₱0.00",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=get_color("primary")
        )
        self.total_restock_label.pack(anchor="e", padx=12, pady=8)

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.restock_tree.bind("<<TreeviewSelect>>", self.on_restock_select)

        # Configure tags for coloring
        self.tree.tag_configure("low", background="#ffcccc")
        self.tree.tag_configure("out", background="#ffaaaa")

    def load_restock_history(self):
        for item in self.restock_tree.get_children():
            self.restock_tree.delete(item)

        restocks = get_all_restock()
        for r in restocks:
            total = float(r['quantity']) * float(r['unit_cost'])
            self.restock_tree.insert("", "end", values=(r['restock_id'], r['product_name'], r['quantity'], f"₱{r['unit_cost']:.2f}", f"₱{total:.2f}", r['restock_date']))

        # Update total restock cost label using database function
        total_cost = get_total_restock_cost()
        self.total_restock_label.configure(text=f"Total Restock Cost: ₱{total_cost:,.2f}")

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_product = int(values[0])
        else:
            self.selected_product = None

    def on_restock_select(self, event):
        selected = self.restock_tree.selection()
        if selected:
            item = self.restock_tree.item(selected[0])
            values = item['values']
            self.selected_restock = int(values[0])
        else:
            self.selected_restock = None

    def load_inventory(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        products = view_products()
        for product in products:
            cost_price = float(product.get('cost_price', 0.0))
            quantity = product['quantity']
            profit = float(product.get('profit', 0.0))
            total_price = float(product.get('total_price', 0.0))
            
            tag = "normal"
            if quantity == 0:
                tag = "out"
            elif quantity <= 10:
                tag = "low"
            self.tree.insert(
                "",
                "end",
                values=(
                    product['product_id'],
                    product['name'],
                    f"{cost_price:.2f}",
                    quantity,
                    f"{profit:.2f}",
                    f"{total_price:.2f}",
                    product['status'],
                ),
                tags=(tag,),
            )

        # Update total inventory value
        total_value = get_total_inventory_value()
        self.total_stock_label.configure(text=f"Total Inventory Value: ₱{total_value:,.2f}")

    def add_product(self):
        self.product_form(None)

    def update_product(self):
        if not self.selected_product:
            messagebox.showwarning("Warning", "Please select a product to update")
            return
        self.product_form(self.selected_product)

    def delete_product(self):
        if not self.selected_product:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to permanently delete this product?"):
            result = delete_product(self.selected_product)
            if isinstance(result, dict):
                if result.get("success"):
                    messagebox.showinfo("Success", result.get("message", "Product deleted successfully!"))
                    self.load_inventory()
                else:
                    messagebox.showerror("Error", result.get("message", "Failed to delete product"))
            elif isinstance(result, int) and result > 0:
                messagebox.showinfo("Success", "Product deleted successfully!")
                self.load_inventory()
            else:
                messagebox.showerror("Error", "Failed to delete product")

    def product_form(self, product_id):
        # Top level window
        self.form_window = ctk.CTkToplevel(self.parent)
        self.form_window.title("Add Product" if product_id is None else "Edit Product")
        self.form_window.geometry("400x150" if product_id is None else "400x550")
        self.form_window.resizable(False, False)
        self.form_window.grab_set()  # Make it modal

        # Fields
        ctk.CTkLabel(self.form_window, text="Name:").pack(pady=5)
        self.name_entry = ctk.CTkEntry(self.form_window)
        self.name_entry.pack(pady=5)

        if product_id is not None:
            # Editing: show all fields
            ctk.CTkLabel(self.form_window, text="Cost Price:").pack(pady=5)
            self.cost_price_entry = ctk.CTkEntry(self.form_window)
            self.cost_price_entry.pack(pady=5)
            self.cost_price_entry.bind("<KeyRelease>", self.update_total_price)

            ctk.CTkLabel(self.form_window, text="Quantity:").pack(pady=5)
            self.qty_entry = ctk.CTkEntry(self.form_window)
            self.qty_entry.pack(pady=5)
            self.qty_entry.bind("<KeyRelease>", self.update_total_price)

            ctk.CTkLabel(self.form_window, text="Total Price:").pack(pady=5)
            self.total_price_entry = ctk.CTkEntry(self.form_window, state="readonly")
            self.total_price_entry.pack(pady=5)

            ctk.CTkLabel(self.form_window, text="Profit:").pack(pady=5)
            self.profit_entry = ctk.CTkEntry(self.form_window)
            self.profit_entry.pack(pady=5)

        # If editing, fill fields
        if product_id:
            product = get_product_by_id(product_id)
            if product:
                cost_price_value = float(product.get('cost_price', 0.0))
                profit_value = float(product.get('profit', 0) or 0.0)
                quantity_value = int(product['quantity'])
                total_price_value = cost_price_value * quantity_value
                
                self.name_entry.insert(0, product['name'])
                self.cost_price_entry.insert(0, str(cost_price_value))
                self.qty_entry.insert(0, str(quantity_value))
                self.total_price_entry.configure(state="normal")
                self.total_price_entry.insert(0, f"{total_price_value:.2f}")
                self.total_price_entry.configure(state="readonly")
                self.profit_entry.insert(0, str(profit_value))

        # Buttons
        btn_frame = ctk.CTkFrame(self.form_window)
        btn_frame.pack(pady=20)
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=lambda: self.save_product(product_id))
        save_btn.pack(side="left", padx=10)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.form_window.destroy)
        cancel_btn.pack(side="right", padx=10)

    def update_total_price(self, event=None):
        """Auto-compute total price when cost price or quantity changes"""
        try:
            cost_price = float(self.cost_price_entry.get().strip() or 0)
            quantity = int(self.qty_entry.get().strip() or 0)
            total_price = cost_price * quantity
            
            self.total_price_entry.configure(state="normal")
            self.total_price_entry.delete(0, "end")
            self.total_price_entry.insert(0, f"{total_price:.2f}")
            self.total_price_entry.configure(state="readonly")
        except ValueError:
            # If invalid input, just clear total price
            self.total_price_entry.configure(state="normal")
            self.total_price_entry.delete(0, "end")
            self.total_price_entry.configure(state="readonly")

    def save_product(self, product_id):
        name = self.name_entry.get().strip()
        try:
            cost_price = float(self.cost_price_entry.get().strip())
            profit = float(self.profit_entry.get().strip())
            total_price = float(self.total_price_entry.get().strip() or 0)
            qty = int(self.qty_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if qty < 0:
            messagebox.showerror("Error", "Quantity must be non-negative")
            return
        if cost_price < 0 or profit < 0:
            messagebox.showerror("Error", "Cost price and profit must be non-negative")
            return

        if product_id:
            update_product(
                product_id,
                name=name,
                cost_price=cost_price,
                profit=profit,
                total_price=total_price,
                quantity=qty,
            )
        else:
            add_product(name, total_price, qty, cost_price=cost_price, profit=profit)
        self.form_window.destroy()
        self.load_inventory()
        self._notify_update()

    def add_restock(self):
        self.restock_form_window = ctk.CTkToplevel(self.parent)
        self.restock_form_window.title("Add Restock")
        self.restock_form_window.geometry("400x450")
        self.restock_form_window.resizable(False, False)
        self.restock_form_window.grab_set()

        # Product option menu
        ctk.CTkLabel(self.restock_form_window, text="Product:").pack(pady=5)
        products = view_products()
        self.product_options = {p['name']: p['product_id'] for p in products}
        self.product_var = ctk.StringVar()
        if products:
            self.product_var.set(products[0]['name'])
        self.product_menu = ctk.CTkOptionMenu(self.restock_form_window, variable=self.product_var, values=list(self.product_options.keys()))
        self.product_menu.pack(pady=5)

        # Quantity
        ctk.CTkLabel(self.restock_form_window, text="Quantity:").pack(pady=5)
        self.restock_qty_entry = ctk.CTkEntry(self.restock_form_window)
        self.restock_qty_entry.pack(pady=5)

        # Unit Cost
        ctk.CTkLabel(self.restock_form_window, text="Unit Cost:").pack(pady=5)
        self.restock_cost_entry = ctk.CTkEntry(self.restock_form_window)
        self.restock_cost_entry.pack(pady=5)

        # Profit
        ctk.CTkLabel(self.restock_form_window, text="Profit:").pack(pady=5)
        self.restock_profit_entry = ctk.CTkEntry(self.restock_form_window)
        self.restock_profit_entry.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self.restock_form_window, corner_radius=0)
        btn_frame.pack(pady=20)
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=self.save_restock)
        save_btn.pack(side="left", padx=10)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.restock_form_window.destroy)
        cancel_btn.pack(side="right", padx=10)

    def save_restock(self):
        product_name = self.product_var.get()
        if not product_name:
            messagebox.showerror("Error", "Select a product")
            return
        product_id = self.product_options[product_name]
        qty_str = self.restock_qty_entry.get().strip()
        cost_str = self.restock_cost_entry.get().strip()
        profit_str = self.restock_profit_entry.get().strip()
        try:
            qty = int(qty_str)
            cost = float(cost_str)
            profit = float(profit_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity, cost, or profit")
            return
        if qty <= 0 or cost < 0 or profit < 0:
            messagebox.showerror("Error", "Quantity must be positive, cost and profit non-negative")
            return
        restock_product(product_id, qty, cost)
        update_product(product_id, profit=profit, total_price=cost + profit)
        self.restock_form_window.destroy()
        self.load_restock_history()
        self.load_inventory()

    def update_restock(self):
        if not self.selected_restock:
            messagebox.showwarning("Warning", "Please select a restock entry to update")
            return
        restock = get_restock_by_id(self.selected_restock)
        if not restock:
            messagebox.showerror("Error", "Restock not found")
            return
        self.restock_form_window = ctk.CTkToplevel(self.parent)
        self.restock_form_window.title("Update Restock")
        self.restock_form_window.geometry("400x300")
        self.restock_form_window.resizable(False, False)
        self.restock_form_window.grab_set()
        ctk.CTkLabel(self.restock_form_window, text="Quantity:").pack(pady=5)
        self.restock_qty_entry = ctk.CTkEntry(self.restock_form_window)
        self.restock_qty_entry.insert(0, str(restock['quantity']))
        self.restock_qty_entry.pack(pady=5)
        ctk.CTkLabel(self.restock_form_window, text="Unit Cost:").pack(pady=5)
        self.restock_cost_entry = ctk.CTkEntry(self.restock_form_window)
        self.restock_cost_entry.insert(0, str(restock['unit_cost']))
        self.restock_cost_entry.pack(pady=5)
        ctk.CTkLabel(self.restock_form_window, text="Profit:").pack(pady=5)
        self.restock_profit_entry = ctk.CTkEntry(self.restock_form_window)
        product = get_product_by_id(restock['product_id'])
        if product:
            self.restock_profit_entry.insert(0, str(product.get('profit', 0)))
        self.restock_profit_entry.pack(pady=5)
        btn_frame = ctk.CTkFrame(self.restock_form_window, corner_radius=0)
        btn_frame.pack(pady=20)
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=self.save_update_restock)
        save_btn.pack(side="left", padx=10)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.restock_form_window.destroy)
        cancel_btn.pack(side="right", padx=10)

    def save_update_restock(self):
        qty_str = self.restock_qty_entry.get().strip()
        cost_str = self.restock_cost_entry.get().strip()
        profit_str = self.restock_profit_entry.get().strip()
        try:
            qty = int(qty_str)
            cost = float(cost_str)
            profit = float(profit_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity, cost, or profit")
            return
        if qty <= 0 or cost < 0 or profit < 0:
            messagebox.showerror("Error", "Quantity must be positive, cost and profit non-negative")
            return
        update_restock(self.selected_restock, qty, cost)
        restock = get_restock_by_id(self.selected_restock)
        if restock:
            update_product(restock['product_id'], profit=profit, total_price=cost + profit)
        self.restock_form_window.destroy()
        self.load_restock_history()
        self.load_inventory()
        self._notify_update()

    def delete_restock(self):
        if not self.selected_restock:
            messagebox.showwarning("Warning", "Please select a restock entry to delete")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this restock entry? This will also update the inventory."):
            delete_restock(self.selected_restock)
            self.load_restock_history()
            self.load_inventory()
            self._notify_update()


class InventoryScreen():
    def __init__(self, parent):
        self.parent = parent
        self.selected_product = None
        self.build_ui()
        self.load_inventory()

    def build_ui(self):
        # Title
        self.title_label = ctk.CTkLabel(self.parent, text="Inventory Management", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)

        # Buttons frame
        self.btn_frame = ctk.CTkFrame(self.parent, corner_radius=0)
        self.btn_frame.pack(fill="x", padx=20, pady=5)

        self.add_btn = ctk.CTkButton(self.btn_frame, text="Add", command=self.add_product)
        self.add_btn.pack(side="left", padx=5)

        self.update_btn = ctk.CTkButton(self.btn_frame, text="Update", command=self.update_product)
        self.update_btn.pack(side="left", padx=5)

        self.delete_btn = ctk.CTkButton(self.btn_frame, text="Delete", fg_color="#c66868", command=self.delete_product)
        self.delete_btn.pack(side="left", padx=5)

        # Treeview frame
        self.tree_frame = ctk.CTkFrame(self.parent, corner_radius=0)
        self.tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Name", "Cost Price", "Quantity", "Profit", "Total Price", "Status"), show="headings", height=2)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Cost Price", text="Cost Price")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Profit", text="Profit")
        self.tree.heading("Total Price", text="Total Price")
        self.tree.heading("Status", text="Status")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=180, anchor="center")
        self.tree.column("Cost Price", width=110, anchor="center")
        self.tree.column("Quantity", width=90, anchor="center")
        self.tree.column("Profit", width=90, anchor="center")
        self.tree.column("Total Price", width=110, anchor="center")
        self.tree.column("Quantity", width=90, anchor="center")
        self.tree.column("Status", width=100, anchor="center")

        # Scrollbars
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        # Total stock amount label frame
        total_frame = ctk.CTkFrame(self.parent, corner_radius=8, fg_color="#74777A")
        total_frame.pack(fill="x", padx=20, pady=(8, 0))

        self.total_stock_label = ctk.CTkLabel(
            total_frame,
            text="Total Inventory Value: ₱0.00",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fbbf24"
        )
        self.total_stock_label.pack(anchor="e", padx=12, pady=8)

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Configure tags for coloring
        self.tree.tag_configure("low", background="#ffcccc")
        self.tree.tag_configure("out", background="#ffaaaa")

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_product = int(values[0])
        else:
            self.selected_product = None

    def load_inventory(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        products = view_products()
        for product in products:
            cost_price = float(product.get('cost_price', 0.0))
            quantity = product['quantity']
            profit = float(product.get('profit', 0.0))
            total_price = float(product.get('total_price', 0.0))
            
            tag = "normal"
            if quantity == 0:
                tag = "out"
            elif quantity <= 10:
                tag = "low"
            self.tree.insert(
                "",
                "end",
                values=(
                    product['product_id'],
                    product['name'],
                    f"{cost_price:.2f}",
                    quantity,
                    f"{profit:.2f}",
                    f"{total_price:.2f}",
                    product['status'],
                ),
                tags=(tag,),
            )

        # Update total inventory value
        total_value = get_total_inventory_value()
        self.total_stock_label.configure(text=f"Total Inventory Value: ₱{total_value:,.2f}")

    def add_product(self):
        self.product_form(None)

    def update_product(self):
        if not self.selected_product:
            messagebox.showwarning("Warning", "Please select a product to update")
            return
        self.product_form(self.selected_product)

    def delete_product(self):
        if not self.selected_product:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to permanently delete this product?"):
            result = delete_product(self.selected_product)
            if isinstance(result, dict):
                if result.get("success"):
                    messagebox.showinfo("Success", result.get("message", "Product deleted successfully!"))
                    self.load_inventory()
                else:
                    messagebox.showerror("Error", result.get("message", "Failed to delete product"))
            elif isinstance(result, int) and result > 0:
                messagebox.showinfo("Success", "Product deleted successfully!")
                self.load_inventory()
            else:
                messagebox.showerror("Error", "Failed to delete product")

    def product_form(self, product_id):
        # Top level window
        self.form_window = ctk.CTkToplevel(self.parent)
        self.form_window.title("Add Product" if product_id is None else "Edit Product")
        self.form_window.geometry("400x150" if product_id is None else "400x550")
        self.form_window.resizable(False, False)
        self.form_window.grab_set()  # Make it modal

        # Fields
        ctk.CTkLabel(self.form_window, text="Name:").pack(pady=5)
        self.name_entry = ctk.CTkEntry(self.form_window)
        self.name_entry.pack(pady=5)

        if product_id is not None:
            # Editing: show all fields
            ctk.CTkLabel(self.form_window, text="Cost Price:").pack(pady=5)
            self.cost_price_entry = ctk.CTkEntry(self.form_window)
            self.cost_price_entry.pack(pady=5)
            self.cost_price_entry.bind("<KeyRelease>", self.update_total_price)

            ctk.CTkLabel(self.form_window, text="Quantity:").pack(pady=5)
            self.qty_entry = ctk.CTkEntry(self.form_window)
            self.qty_entry.pack(pady=5)
            self.qty_entry.bind("<KeyRelease>", self.update_total_price)

            ctk.CTkLabel(self.form_window, text="Total Price:").pack(pady=5)
            self.total_price_entry = ctk.CTkEntry(self.form_window, state="readonly")
            self.total_price_entry.pack(pady=5)

            ctk.CTkLabel(self.form_window, text="Profit:").pack(pady=5)
            self.profit_entry = ctk.CTkEntry(self.form_window)
            self.profit_entry.pack(pady=5)

        # If editing, fill fields
        if product_id:
            product = get_product_by_id(product_id)
            if product:
                cost_price_value = Decimal(str(product.get('cost_price', 0.0)))
                quantity_value = int(product['quantity'])
                profit_value = Decimal(str(product.get('profit', 0)))
                total_price_value = Decimal(str(product.get('total_price', cost_price_value * quantity_value)))

                self.name_entry.insert(0, product['name'])
                self.cost_price_entry.insert(0, f"{cost_price_value:.2f}")
                self.qty_entry.insert(0, str(quantity_value))
                self.total_price_entry.configure(state="normal")
                self.total_price_entry.insert(0, f"{total_price_value:.2f}")
                self.total_price_entry.configure(state="readonly")
                self.profit_entry.insert(0, f"{profit_value:.2f}")

        # Buttons
        btn_frame = ctk.CTkFrame(self.form_window, corner_radius=0)
        btn_frame.pack(pady=20)
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=lambda: self.save_product(product_id))
        save_btn.pack(side="left", padx=10)
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.form_window.destroy)
        cancel_btn.pack(side="right", padx=10)

    def update_total_price(self, event=None):
        """Auto-compute total price when cost price or quantity changes"""
        try:
            cost_price = float(self.cost_price_entry.get().strip() or 0)
            quantity = int(self.qty_entry.get().strip() or 0)
            total_price = cost_price * quantity
            
            self.total_price_entry.configure(state="normal")
            self.total_price_entry.delete(0, "end")
            self.total_price_entry.insert(0, f"{total_price:.2f}")
            self.total_price_entry.configure(state="readonly")
        except ValueError:
            # If invalid input, just clear total price
            self.total_price_entry.configure(state="normal")
            self.total_price_entry.delete(0, "end")
            self.total_price_entry.configure(state="readonly")

    def save_product(self, product_id):
        name = self.name_entry.get().strip()
        try:
            cost_price = float(self.cost_price_entry.get().strip())
            profit = float(self.profit_entry.get().strip())
            total_price = float(self.total_price_entry.get().strip() or 0)
            qty = int(self.qty_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if qty < 0:
            messagebox.showerror("Error", "Quantity must be non-negative")
            return
        if cost_price < 0 or profit < 0:
            messagebox.showerror("Error", "Cost price and profit must be non-negative")
            return

        if product_id:
            update_product(
                product_id,
                name=name,
                cost_price=cost_price,
                profit=profit,
                total_price=total_price,
                quantity=qty,
            )
        else:
            add_product(name, total_price, qty, cost_price=cost_price, profit=profit)
        self.form_window.destroy()
        self.load_inventory()
