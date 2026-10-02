import json
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# LOGIN PROTECTION
# =========================================================

@app.before_request
def require_login():
    public_pages = {"login", "register", "static"}

    if request.endpoint in public_pages:
        return

    if "user" not in session:
        return redirect(url_for("login"))


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = [
    {
        "id": 1,
        "name": "USB Type-C Cable",
        "category": "Cables",
        "price": 99,
        "description": "Durable everyday USB Type-C cable.",
        "emoji": "🔌"
    },
    {
        "id": 2,
        "name": "Wireless Mouse",
        "category": "Accessories",
        "price": 249,
        "description": "Compact wireless mouse for school and office work.",
        "emoji": "🖱️"
    },
    {
        "id": 3,
        "name": "USB Flash Drive 32GB",
        "category": "Storage",
        "price": 199,
        "description": "Portable storage for school files and projects.",
        "emoji": "💾"
    },
    {
        "id": 4,
        "name": "Cable Organizer",
        "category": "Accessories",
        "price": 59,
        "description": "Keep your cables neat and organized.",
        "emoji": "🧩"
    },
    {
        "id": 5,
        "name": "Mouse Pad",
        "category": "Accessories",
        "price": 89,
        "description": "Simple desk mat for comfortable mouse use.",
        "emoji": "🖥️"
    },
    {
        "id": 6,
        "name": "Arduino UNO Compatible Board",
        "category": "Electronics",
        "price": 399,
        "description": "Beginner-friendly microcontroller board for projects.",
        "emoji": "⚡"
    },
]


DOWNLOADS = [
    {
        "name": "Visual Studio Code",
        "description": "Code editor for programming and web development.",
        "url": "https://code.visualstudio.com/download"
    },
    {
        "name": "Arduino IDE",
        "description": "Official IDE for Arduino development.",
        "url": "https://www.arduino.cc/en/software"
    },
    {
        "name": "Python",
        "description": "Official Python downloads.",
        "url": "https://www.python.org/downloads/"
    },
    {
        "name": "Git",
        "description": "Official Git downloads.",
        "url": "https://git-scm.com/downloads"
    },
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_product(product_id):
    return next(
        (p for p in PRODUCTS if p["id"] == product_id),
        None
    )


def current_user():
    return session.get("user")


def supabase_enabled():
    return supabase is not None


# =========================================================
# MAIN PAGES
# =========================================================

@app.route("/")
def home():
    return render_template(
        "home.html",
        products=PRODUCTS,
        user=current_user()
    )


@app.route("/products")
def products():
    return render_template(
        "products.html",
        products=PRODUCTS,
        user=current_user()
    )


@app.route("/product/<int:product_id>")
def product(product_id):
    item = get_product(product_id)

    if not item:
        return "Product not found", 404

    return render_template(
        "product.html",
        product=item,
        user=current_user()
    )


@app.route("/budget")
def budget():
    return render_template(
        "budget.html",
        products=PRODUCTS,
        user=current_user()
    )


@app.route("/downloads")
def downloads():
    return render_template(
        "downloads.html",
        downloads=DOWNLOADS,
        user=current_user()
    )


@app.route("/bundles")
def bundles():
    return render_template(
        "bundles.html",
        user=current_user()
    )


@app.route("/cart")
def cart():
    return render_template(
        "cart.html",
        user=current_user()
    )


# =========================================================
# CHECKOUT / PLACE ORDER
# =========================================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if request.method == "POST":

        user = current_user()

        if not user:
            flash(
                "Please log in before placing an order.",
                "error"
            )
            return redirect(url_for("login"))

        # Get checkout form data
        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        contact = request.form.get(
            "contact",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            ""
        ).strip()

        items_raw = request.form.get(
            "cart_items",
            ""
        ).strip()

        total_raw = request.form.get(
            "total_amount",
            "0"
        ).strip()

        # Validate checkout details
        if not full_name or not contact or not address or not payment_method:
            flash(
                "Please complete all checkout details.",
                "error"
            )
            return redirect(url_for("checkout"))

        # Convert total
        try:
            total = Decimal(total_raw)

        except InvalidOperation:
            flash(
                "Invalid order total.",
                "error"
            )
            return redirect(url_for("checkout"))

        # Convert cart JSON
        try:
            parsed_items = json.loads(items_raw)

            if not isinstance(parsed_items, list) or len(parsed_items) == 0:
                flash(
                    "Your cart is empty.",
                    "error"
                )
                return redirect(url_for("cart"))

        except (json.JSONDecodeError, TypeError):
            flash(
                "Invalid cart data.",
                "error"
            )
            return redirect(url_for("cart"))

        # =================================================
        # DEMO MODE
        # =================================================

        if not supabase_enabled():

            demo_orders = session.get("orders", [])

            demo_order = {
                "id": len(demo_orders) + 1,
                "user_id": user["id"],
                "full_name": full_name,
                "contact": contact,
                "address": address,
                "payment_method": payment_method,
                "total_amount": float(total),
                "status": "To Ship",
                "items": parsed_items
            }

            demo_orders.insert(
                0,
                demo_order
            )

            session["orders"] = demo_orders
            session.modified = True

            flash(
                "Order placed successfully!",
                "success"
            )

            return redirect(url_for("orders"))

        # =================================================
        # SUPABASE MODE
        # =================================================

        try:

            # Create order
            order_result = (
                supabase
                .table("orders")
                .insert({
                    "user_id": user["id"],
                    "full_name": full_name,
                    "contact": contact,
                    "address": address,
                    "payment_method": payment_method,
                    "total_amount": float(total),
                    "status": "To Ship"
                })
                .execute()
            )

            if not order_result.data:
                raise Exception(
                    "Order was not created."
                )

            order_id = order_result.data[0]["id"]

            # Create order items
            order_items = []

            for item in parsed_items:

                order_items.append({
                    "order_id": order_id,
                    "product_id": item.get("product_id"),
                    "quantity": int(
                        item.get("quantity", 1)
                    ),
                    "unit_price": float(
                        item.get("unit_price", 0)
                    )
                })

            if order_items:
                (
                    supabase
                    .table("order_items")
                    .insert(order_items)
                    .execute()
                )

            flash(
                "Order placed successfully! Check your Saved Orders.",
                "success"
            )

            return redirect(
                url_for("orders")
            )

        except Exception as e:

            print(
                "CHECKOUT ERROR:",
                e
            )

            flash(
                "Order could not be saved. Please check your Supabase connection.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

    return render_template(
        "checkout.html",
        user=current_user()
    )


# =========================================================
# SAVED ORDERS / MY ORDERS
# =========================================================

@app.route("/orders")
def orders():

    user = current_user()
    saved_orders = []

    if not user:
        return redirect(
            url_for("login")
        )

    # =====================================================
    # SUPABASE
    # =====================================================

    if supabase_enabled():

        try:

            result = (
                supabase
                .table("orders")
                .select("*")
                .eq(
                    "user_id",
                    user["id"]
                )
                .order(
                    "created_at",
                    desc=True
                )
                .execute()
            )

            saved_orders = result.data or []

        except Exception as e:

            print(
                "ORDERS ERROR:",
                e
            )

            flash(
                "Could not load your saved orders.",
                "error"
            )

            saved_orders = []

    # =====================================================
    # DEMO MODE
    # =====================================================

    else:

        saved_orders = session.get(
            "orders",
            []
        )

        # Only show orders belonging to current user
        saved_orders = [
            order
            for order in saved_orders
            if order.get("user_id") == user["id"]
        ]

    return render_template(
        "orders.html",
        orders=saved_orders,
        user=user
    )


# =========================================================
# REMOVE ORDER
# =========================================================

@app.route(
    "/orders/<order_id>/remove",
    methods=["POST"]
)
def remove_order(order_id):

    user = current_user()

    if not user:
        return redirect(
            url_for("login")
        )

    # =====================================================
    # DEMO MODE
    # =====================================================

    if not supabase_enabled():

        demo_orders = session.get(
            "orders",
            []
        )

        new_orders = []

        for order in demo_orders:

            # Only remove the order if:
            # 1. It belongs to the logged-in user
            # 2. The order ID matches

            if (
                str(order.get("id")) == str(order_id)
                and str(order.get("user_id")) == str(user["id"])
            ):
                continue

            new_orders.append(order)

        session["orders"] = new_orders
        session.modified = True

        flash(
            "Order removed successfully.",
            "success"
        )

        return redirect(
            url_for("orders")
        )

    # =====================================================
    # SUPABASE MODE
    # =====================================================

    try:

        # First find the order belonging to this user
        order_result = (
            supabase
            .table("orders")
            .select("id")
            .eq(
                "id",
                order_id
            )
            .eq(
                "user_id",
                user["id"]
            )
            .execute()
        )

        if not order_result.data:
            flash(
                "Order not found.",
                "error"
            )
            return redirect(
                url_for("orders")
            )

        # Delete order items first
        (
            supabase
            .table("order_items")
            .delete()
            .eq(
                "order_id",
                order_id
            )
            .execute()
        )

        # Delete the order itself
        (
            supabase
            .table("orders")
            .delete()
            .eq(
                "id",
                order_id
            )
            .eq(
                "user_id",
                user["id"]
            )
            .execute()
        )

        flash(
            "Order removed successfully.",
            "success"
        )

    except Exception as e:

        print(
            "REMOVE ORDER ERROR:",
            e
        )

        flash(
            "Could not remove the order.",
            "error"
        )

    return redirect(
        url_for("orders")
    )


# =========================================================
# OTHER PAGES
# =========================================================

@app.route("/wishlist")
def wishlist():
    return render_template(
        "wishlist.html",
        user=current_user()
    )


@app.route("/profile")
def profile():
    return render_template(
        "profile.html",
        user=current_user()
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        account_type = request.form.get(
            "account_type",
            ""
        ).strip()

        if not email or not password or not account_type:

            flash(
                "Please complete all login fields.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # Demo mode
        if not supabase_enabled():

            session["user"] = {
                "id": "demo-user",
                "email": email,
                "account_type": account_type
            }

            return redirect(
                url_for("home")
            )

        try:

            auth = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user = auth.user

            if not user:
                raise ValueError(
                    "Login failed"
                )

            session["user"] = {
                "id": user.id,
                "email": user.email,
                "account_type": account_type
            }

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print(
                "LOGIN ERROR:",
                e
            )

            flash(
                "Login failed. Please check your email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

    return render_template(
        "login.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        account_type = request.form.get(
            "account_type",
            ""
        ).strip()

        school = request.form.get(
            "school",
            ""
        ).strip()

        contact = request.form.get(
            "contact",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not all([
            name,
            email,
            account_type,
            school,
            password,
            confirm_password
        ]):

            flash(
                "Please complete all required fields.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # Demo mode
        if not supabase_enabled():

            return render_template(
                "registration_success.html",
                name=name,
                account_type=account_type,
                school=school
            )

        try:

            auth = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": name,
                        "account_type": account_type,
                        "school": school,
                        "contact": contact
                    }
                }
            })

            if not auth.user:
                raise ValueError(
                    "Registration failed"
                )

            return render_template(
                "registration_success.html",
                name=name,
                account_type=account_type,
                school=school
            )

        except Exception as e:

            print(
                "REGISTER ERROR:",
                e
            )

            flash(
                "Registration failed. The email may already be registered or Supabase needs configuration.",
                "error"
            )

            return render_template(
                "register.html"
            )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    if supabase_enabled():

        try:
            supabase.auth.sign_out()
        except Exception:
            pass

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# ABOUT / CONTACT / ADMIN
# =========================================================

@app.route("/about")
def about():
    return render_template(
        "about.html",
        user=current_user()
    )


@app.route("/contact")
def contact():
    return render_template(
        "contact.html",
        user=current_user()
    )


@app.route("/admin")
def admin():
    return render_template(
        "admin.html",
        user=current_user()
    )


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)