import json
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

from supabase import Client, create_client

# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()

supabase: Client | None = None


# =========================================================
# SUPABASE CONNECTION
# =========================================================

if SUPABASE_URL and SUPABASE_KEY:

    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

        print("SUPABASE CONNECTED")

    except Exception as e:

        print(
            "SUPABASE CONNECTION ERROR:",
            repr(e)
        )

        supabase = None

else:

    print("SUPABASE NOT CONFIGURED")


# =========================================================
# LOGIN PROTECTION
# =========================================================

@app.before_request
def require_login():

    public_pages = {
        "login",
        "admin_login",
        "register",
        "static"
    }

    if request.endpoint in public_pages:
        return

    if "user" not in session:
        return redirect(
            url_for("login")
        )


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
    }

]


# =========================================================
# DOWNLOADS
# =========================================================

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
    }

]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def current_user():

    return session.get("user")


def supabase_enabled():

    return supabase is not None


def get_product(product_id):

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        return None

    return next(
        (
            product
            for product in PRODUCTS
            if product["id"] == product_id
        ),
        None
    )


def get_seller_profile(user_id):
    """Return a seller profile without breaking pages if the table is unavailable."""
    if not supabase_enabled() or not user_id:
        return None

    try:
        result = (
            supabase.table("seller_profiles")
            .select("user_id, shop_name, bio, created_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print("SELLER PROFILE LOAD ERROR:", repr(e))
        return None


def get_product_reviews(product_id):
    """Fetch public reviews for one product; return an empty list on failure."""
    if not supabase_enabled():
        return []

    try:
        result = (
            supabase.table("product_reviews")
            .select("id, product_id, reviewer_id, rating, comment, created_at")
            .eq("product_id", int(product_id))
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print("PRODUCT REVIEWS LOAD ERROR:", repr(e))
        return []


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "home.html",
        products=PRODUCTS,
        user=current_user()
    )


# =========================================================
# PRODUCTS
# =========================================================

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

    reviews = get_product_reviews(product_id)
    review_count = len(reviews)
    average_rating = (
        round(sum(int(review.get("rating") or 0) for review in reviews) / review_count, 1)
        if review_count else 0
    )

    return render_template(
        "product.html",
        product=item,
        reviews=reviews,
        review_count=review_count,
        average_rating=average_rating,
        user=current_user()
    )


@app.route("/product/<int:product_id>/review", methods=["POST"])
def submit_review(product_id):
    """Create or update the logged-in user's review for a product."""
    user = current_user()
    if not user or not user.get("id") or user.get("id") == "demo-user":
        flash("Please log in with a real account to leave a review.", "error")
        return redirect(url_for("login"))

    if not supabase_enabled():
        flash("Reviews require the Supabase connection.", "error")
        return redirect(url_for("product", product_id=product_id))

    item = get_product(product_id)
    if not item:
        return "Product not found", 404

    try:
        rating = int(request.form.get("rating", "0"))
    except (TypeError, ValueError):
        rating = 0
    comment = request.form.get("comment", "").strip()

    if rating < 1 or rating > 5:
        flash("Please choose a rating from 1 to 5 stars.", "error")
        return redirect(url_for("product", product_id=product_id))

    if len(comment) > 2000:
        flash("Your review must be 2,000 characters or fewer.", "error")
        return redirect(url_for("product", product_id=product_id))

    try:
        # product_reviews.product_id references public.products(id), so confirm
        # this product exists in the database before attempting the insert.
        product_check = (
            supabase.table("products")
            .select("id")
            .eq("id", product_id)
            .limit(1)
            .execute()
        )
        if not product_check.data:
            flash(
                "This sample product is not linked to a row in Supabase products yet, so it cannot receive reviews. We need to connect the product catalog next.",
                "error"
            )
            return redirect(url_for("product", product_id=product_id))

        supabase.table("product_reviews").upsert(
            {
                "product_id": product_id,
                "reviewer_id": user["id"],
                "rating": rating,
                "comment": comment
            },
            on_conflict="product_id,reviewer_id"
        ).execute()

        flash("Your review has been saved.", "success")
    except Exception as e:
        print("SUBMIT REVIEW ERROR:", repr(e))
        flash(
            "Could not save your review. Check the product_reviews table policies and Supabase login session.",
            "error"
        )

    return redirect(url_for("product", product_id=product_id))


# =========================================================
# OTHER PAGES
# =========================================================

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


@app.route("/wishlist")
def wishlist():

    return render_template(
        "wishlist.html",
        user=current_user()
    )


@app.route("/profile")
def profile():

    user = current_user()
    seller_profile = get_seller_profile(user.get("id") if user else None)

    return render_template(
        "profile.html",
        user=user,
        seller_profile=seller_profile
    )


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


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Separate admin sign-in using the existing Supabase account."""
    if request.method == "GET":
        return render_template("admin_login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not ADMIN_EMAIL:
        flash("Admin login is not configured yet. Set ADMIN_EMAIL in Render.", "error")
        return render_template("admin_login.html"), 503

    if not supabase_enabled():
        flash("Admin login requires the configured Supabase connection.", "error")
        return render_template("admin_login.html"), 503

    if not email or not password:
        flash("Please enter your admin email and password.", "error")
        return render_template("admin_login.html"), 400

    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})

        # Never trust the account_type dropdown or user metadata for admin access.
        authenticated_email = (result.user.email or "").strip().lower() if result.user else ""
        if not result.user or authenticated_email != ADMIN_EMAIL:
            flash("This account is not authorized for admin access.", "error")
            return render_template("admin_login.html"), 403

        if result.session:
            supabase.auth.set_session(
                result.session.access_token,
                result.session.refresh_token
            )

        session.clear()
        session["user"] = {
            "id": result.user.id,
            "email": authenticated_email,
            "account_type": "admin"
        }
        return redirect(url_for("admin"))

    except Exception as e:
        print("ADMIN LOGIN ERROR:", repr(e))
        flash("Admin login failed. Check your email and password.", "error")
        return render_template("admin_login.html"), 401


@app.route("/admin")
def admin():
    user = current_user()

    # Enforce authorization on the server, even if a user changes the URL.
    if not ADMIN_EMAIL or not user or (user.get("email") or "").strip().lower() != ADMIN_EMAIL:
        flash("You are not authorized to access the admin dashboard.", "error")
        return redirect(url_for("home"))

    all_orders = []
    customer_summary = {}
    total_sales = 0.0
    error_message = None

    if supabase_enabled():
        try:
            result = supabase.table("orders").select("*").order("created_at", desc=True).execute()
            all_orders = result.data or []

            for order in all_orders:
                status = str(order.get("status") or "To Ship")
                amount = float(order.get("total_amount") or 0)
                # Cancelled orders are not counted as sales.
                if status.lower() != "cancelled":
                    total_sales += amount

                customer_id = str(order.get("user_id") or "unknown")
                customer_name = (order.get("full_name") or "Customer").strip()
                customer_email = (order.get("email") or "").strip()
                if customer_id not in customer_summary:
                    customer_summary[customer_id] = {
                        "user_id": customer_id,
                        "name": customer_name,
                        "email": customer_email,
                        "order_count": 0,
                        "total_spent": 0.0
                    }
                customer_summary[customer_id]["order_count"] += 1
                if status.lower() != "cancelled":
                    customer_summary[customer_id]["total_spent"] += amount

                order["items"] = []
                try:
                    item_result = supabase.table("order_items").select("*").eq("order_id", order["id"]).execute()
                    for order_item in (item_result.data or []):
                        product = get_product(order_item.get("product_id"))
                        quantity = int(order_item.get("quantity") or 1)
                        if product:
                            order["items"].append({
                                "name": product["name"],
                                "quantity": quantity,
                                "subtotal": float(order_item.get("unit_price") or product["price"]) * quantity
                            })
                except Exception as item_error:
                    print("ADMIN ORDER ITEMS ERROR:", repr(item_error))

            # Show customers with the highest number of orders first.
            customer_summary = sorted(
                customer_summary.values(),
                key=lambda customer: customer["order_count"],
                reverse=True
            )
        except Exception as e:
            print("ADMIN DASHBOARD ERROR:", repr(e))
            error_message = "Could not load order data. Check the Supabase orders and order_items tables."
    else:
        error_message = "Supabase is not configured. Admin dashboard requires saved Supabase orders."

    return render_template(
        "admin.html",
        user=user,
        orders=all_orders,
        customers=customer_summary,
        total_orders=len(all_orders),
        total_sales=total_sales,
        error_message=error_message
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if request.method == "GET":

        return render_template(
            "checkout.html",
            user=current_user()
        )

    user = current_user()

    if not user:

        flash(
            "Please log in before placing an order.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # -----------------------------------------------------
    # CUSTOMER INFORMATION
    # -----------------------------------------------------

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

    total_raw = request.form.get(
        "total_amount",
        "0"
    ).strip()

    cart_items_raw = request.form.get(
        "cart_items",
        "[]"
    )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not full_name:

        flash(
            "Please enter your full name.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )

    if not contact:

        flash(
            "Please enter your contact number.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )

    if not address:

        flash(
            "Please enter your delivery address.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )

    if not payment_method:

        flash(
            "Please select a payment method.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )

    # -----------------------------------------------------
    # TOTAL
    # -----------------------------------------------------

    try:

        total = Decimal(total_raw)

    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):

        flash(
            "Invalid order total.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )

    # -----------------------------------------------------
    # CART ITEMS
    # -----------------------------------------------------

    try:

        cart_items = json.loads(
            cart_items_raw
        )

        if not isinstance(cart_items, list):
            cart_items = []

    except Exception:

        cart_items = []

    if not cart_items:

        flash(
            "Your cart is empty.",
            "error"
        )

        return redirect(
            url_for("cart")
        )

    # =====================================================
    # DEMO MODE
    # =====================================================

    if not supabase_enabled():

        saved_orders = session.get(
            "orders",
            []
        )

        new_order = {

            "id": len(saved_orders) + 1,

            "user_id": user["id"],

            "full_name": full_name,

            "contact": contact,

            "address": address,

            "payment_method": payment_method,

            "total_amount": float(total),

            "status": "To Ship",

            "items": cart_items

        }

        saved_orders.insert(
            0,
            new_order
        )

        session["orders"] = saved_orders

        session.modified = True

        flash(
            "Order placed successfully!",
            "success"
        )

        return redirect(
            url_for("orders")
        )

    # =====================================================
    # SUPABASE ORDER
    # =====================================================

    try:

        print("========================================")
        print("CREATING ORDER")

        print(
            "USER ID:",
            user["id"]
        )

        print(
            "USER EMAIL:",
            user.get("email")
        )

        order_data = {

            "user_id": user["id"],

            "full_name": full_name,

            "contact": contact,

            "address": address,

            "payment_method": payment_method,

            "total_amount": float(total),

            "status": "To Ship"

        }

        print(
            "ORDER DATA:",
            order_data
        )

        # -------------------------------------------------
        # INSERT ORDER
        # -------------------------------------------------

        order_result = (

            supabase

            .table("orders")

            .insert(order_data)

            .execute()

        )

        print(
            "ORDER RESULT:",
            order_result.data
        )

        if not order_result.data:

            raise Exception(
                "Supabase did not return the new order."
            )

        new_order = order_result.data[0]

        order_id = new_order["id"]

        print(
            "NEW ORDER ID:",
            order_id
        )

        # -------------------------------------------------
        # INSERT ORDER ITEMS
        # -------------------------------------------------

        order_items = []

        for item in cart_items:

            try:

                product_id = int(
                    item.get("product_id")
                )

                quantity = int(
                    item.get(
                        "quantity",
                        1
                    )
                )

                unit_price = float(
                    item.get(
                        "unit_price",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            product = get_product(product_id)

            if not product:
                continue

            if quantity < 1:
                quantity = 1

            order_items.append({

                "order_id": order_id,

                "product_id": product_id,

                "quantity": quantity,

                "unit_price": unit_price

            })

        print(
            "ORDER ITEMS:",
            order_items
        )

        if order_items:

            items_result = (

                supabase

                .table("order_items")

                .insert(order_items)

                .execute()

            )

            print(
                "ORDER ITEMS RESULT:",
                items_result.data
            )

        print(
            "ORDER SAVED SUCCESSFULLY"
        )

        print("========================================")

        flash(
            "Order placed successfully! Check your Saved Orders.",
            "success"
        )

        return redirect(
            url_for("orders")
        )

    except Exception as e:

        print("========================================")

        print(
            "CHECKOUT ERROR:",
            repr(e)
        )

        print(
            "CHECKOUT ERROR TYPE:",
            type(e).__name__
        )

        print("========================================")

        flash(
            "Order could not be saved. Please try again.",
            "error"
        )

        return redirect(
            url_for("checkout")
        )


# =========================================================
# SAVED ORDERS
# =========================================================

@app.route("/orders")
def orders():

    user = current_user()

    if not user:

        return redirect(
            url_for("login")
        )

    saved_orders = []

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

            saved_orders = (
                result.data or []
            )

            # -------------------------------------------------
            # LOAD ORDER ITEMS
            # -------------------------------------------------

            for order in saved_orders:

                order["items"] = []

                try:

                    items_result = (

                        supabase

                        .table("order_items")

                        .select("*")

                        .eq(
                            "order_id",
                            order["id"]
                        )

                        .execute()

                    )

                    items = (
                        items_result.data or []
                    )

                    for item in items:

                        product = get_product(
                            item.get("product_id")
                        )

                        if product:

                            quantity = int(
                                item.get(
                                    "quantity",
                                    1
                                )
                            )

                            unit_price = float(
                                item.get(
                                    "unit_price",
                                    product["price"]
                                )
                            )

                            order["items"].append({

                                "name": product["name"],

                                "quantity": quantity,

                                "unit_price": unit_price,

                                "subtotal":
                                    unit_price * quantity

                            })

                except Exception as item_error:

                    print(
                        "ORDER ITEMS ERROR:",
                        repr(item_error)
                    )

                    order["items"] = []

            print(
                "SAVED ORDERS:",
                saved_orders
            )

        except Exception as e:

            print(
                "ORDERS ERROR:",
                repr(e)
            )

            flash(
                "Could not load your saved orders.",
                "error"
            )

    # =====================================================
    # DEMO MODE
    # =====================================================

    else:

        all_orders = session.get(
            "orders",
            []
        )

        saved_orders = [

            order

            for order in all_orders

            if str(
                order.get("user_id")
            )
            == str(
                user["id"]
            )

        ]

    return render_template(
        "orders.html",
        orders=saved_orders,
        user=user
    )


# =========================================================
# CANCEL ORDER
# =========================================================

@app.route(
    "/orders/<uuid:order_id>/cancel",
    methods=["POST"]
)
def cancel_order(order_id):

    user = current_user()

    if not user:

        flash(
            "Please log in first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # =====================================================
    # DEMO MODE
    # =====================================================

    if not supabase_enabled():

        saved_orders = session.get(
            "orders",
            []
        )

        cancelled = False

        for order in saved_orders:

            if (

                str(
                    order.get("id")
                )
                == str(order_id)

                and

                str(
                    order.get("user_id")
                )
                == str(user["id"])

                and

                order.get("status")
                == "To Ship"

            ):

                order["status"] = "Cancelled"

                cancelled = True

                break

        session["orders"] = saved_orders

        session.modified = True

        if cancelled:

            flash(
                "Order cancelled successfully.",
                "success"
            )

        else:

            flash(
                "This order can no longer be cancelled.",
                "error"
            )

        return redirect(
            url_for("orders")
        )

    # =====================================================
    # SUPABASE
    # =====================================================

    try:

        result = (

            supabase

            .table("orders")

            .update({
                "status": "Cancelled"
            })

            .eq(
                "id",
                str(order_id)
            )

            .eq(
                "user_id",
                user["id"]
            )

            .eq(
                "status",
                "To Ship"
            )

            .execute()

        )

        if result.data:

            flash(
                "Order cancelled successfully.",
                "success"
            )

        else:

            flash(
                "This order can no longer be cancelled.",
                "error"
            )

    except Exception as e:

        print(
            "CANCEL ORDER ERROR:",
            repr(e)
        )

        flash(
            "Could not cancel the order.",
            "error"
        )

    return redirect(
        url_for("orders")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
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

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        # -------------------------------------------------
        # DEMO MODE
        # -------------------------------------------------

        if not supabase_enabled():

            session["user"] = {

                "id": "demo-user",

                "email": email,

                "account_type": account_type

            }

            return redirect(
                url_for("home")
            )

        # -------------------------------------------------
        # SUPABASE LOGIN
        # -------------------------------------------------

        try:

            result = (

                supabase

                .auth

                .sign_in_with_password({

                    "email": email,

                    "password": password

                })

            )

            if not result.user:

                raise Exception(
                    "Login failed."
                )

            # -------------------------------------------------
            # SET SUPABASE SESSION
            # -------------------------------------------------

            if result.session:

                supabase.auth.set_session(

                    result.session.access_token,

                    result.session.refresh_token

                )

                print(
                    "SUPABASE AUTH SESSION SET"
                )

            session["user"] = {

                "id": result.user.id,

                "email": result.user.email,

                "account_type": account_type

            }

            print(
                "LOGGED IN USER ID:",
                result.user.id
            )

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print(
                "LOGIN ERROR:",
                repr(e)
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

@app.route(
    "/register",
    methods=["GET", "POST"]
)
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

        if (

            not name
            or not email
            or not account_type
            or not school
            or not password
            or not confirm_password

        ):

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

        # =================================================
        # DEMO MODE
        # =================================================

        if not supabase_enabled():

            return render_template(
                "registration_success.html",
                name=name,
                account_type=account_type,
                school=school
            )

        # =================================================
        # SUPABASE REGISTER
        # =================================================

        try:

            result = (

                supabase

                .auth

                .sign_up({

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

            )

            if not result.user:

                raise Exception(
                    "Registration failed."
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
                repr(e)
            )

            flash(
                "Registration failed. Please check your information.",
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

        except Exception as e:

            print(
                "LOGOUT ERROR:",
                repr(e)
            )

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )