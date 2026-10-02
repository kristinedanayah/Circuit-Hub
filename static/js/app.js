function addDemoItem(id, name, price) {
    const cart = JSON.parse(
        localStorage.getItem("circuitHubCart") || "[]"
    );

    const existing = cart.find(
        item => item.product_id === id
    );

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            product_id: id,
            name: name,
            unit_price: Number(price),
            quantity: 1
        });
    }

    localStorage.setItem(
        "circuitHubCart",
        JSON.stringify(cart)
    );

    showCartNotification(name + " added to cart.");
}

function showCartNotification(message) {
    let notification = document.getElementById("cartNotification");

    if (!notification) {
        notification = document.createElement("div");
        notification.id = "cartNotification";
        notification.className = "cart-notification";
        document.body.appendChild(notification);
    }

    notification.textContent = "✓ " + message;
    notification.classList.add("show");

    setTimeout(() => {
        notification.classList.remove("show");
    }, 2000);
}
function findBudgetSet() {
    const input = document.getElementById("budgetInput");
    const results = document.getElementById("budgetResults");
    const message = document.getElementById("budgetMessage");
    if (!input || !results) return;

    const budget = Number(input.value);
    if (!budget || budget <= 0) {
        message.textContent = "Please enter a valid budget.";
        return;
    }

    let total = 0;
    const selected = [];

    for (const p of budgetProducts) {
        if (total + Number(p.price) <= budget) {
            selected.push(p);
            total += Number(p.price);
        }
    }

    results.innerHTML = selected.map(p => `
        <article class="product-card">
            <div class="product-icon">${p.emoji}</div>
            <span class="category">${p.category}</span>
            <h3>${p.name}</h3>
            <p>${p.description}</p>
            <div class="product-bottom">
                <strong>₱${Number(p.price).toFixed(2)}</strong>
            </div>
        </article>
    `).join("");

    message.textContent = selected.length
        ? `Suggested set: ${selected.length} item(s), total ₱${total.toFixed(2)}.`
        : "No combination fits that budget yet.";
}
