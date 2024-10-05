import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Custom filter for formatting numbers as USD
app.jinja_env.filters["usd"] = usd

# Home route displays portfolio


@app.route("/")
@login_required
def index():
    # Query for user's cash and portfolio
    user_id = session["user_id"]
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
    rows = db.execute(
        "SELECT symbol, SUM(shares) as shares FROM portfolio WHERE user_id = ? GROUP BY symbol", user_id)

    # Query current prices for stocks
    stocks = []
    for row in rows:
        stock = lookup(row["symbol"])
        total = stock["price"] * row["shares"]
        stocks.append({
            "symbol": row["symbol"],
            "name": stock["name"],
            "shares": row["shares"],
            "price": usd(stock["price"]),
            "total": usd(total)
        })

    return render_template("index.html", stocks=stocks, cash=usd(cash))


# Quote route allows user to lookup stock prices
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        stock = lookup(symbol)

        if not stock:
            return apology("invalid stock symbol", 400)

        return render_template("quoted.html", name=stock["name"], symbol=stock["symbol"], price=usd(stock["price"]))
    else:
        return render_template("quote.html")

# History Route


@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    transactions = db.execute(
        "SELECT symbol, shares, price, transacted FROM transactions WHERE user_id = ?", user_id)
    return render_template("history.html", transactions=transactions)


# Buy route allows user to buy stocks
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("Shares must be a whole number", 400)

        if shares <= 0:
            return apology("Shares must be a positive number", 400)

        stock = lookup(symbol)
        if not stock:
            return apology("invalid stock symbol", 400)

        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        total_cost = shares * stock["price"]
        if total_cost > cash:
            return apology("can't afford", 400)

        # Update user's cash and add stock to portfolio
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, user_id)
        db.execute("INSERT INTO portfolio (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, shares, stock["price"])

        # Log the transaction in the transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, shares, stock["price"])

        return redirect("/")
    else:
        return render_template("buy.html")


# Register route for new users
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("must fill out all fields", 400)

        if password != confirmation:
            return apology("passwords don't match", 400)

        # Check if username exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) > 0:
            return apology("username already exists", 400)

        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        return redirect("/login")
    else:
        return render_template("register.html")

# Sell Route


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("Shares must be a whole number", 400)

        if shares <= 0:
            return apology("Shares must be a positive number", 400)

        # Query for user's shares of that stock
        user_id = session["user_id"]
        stock_shares = db.execute("SELECT SUM(shares) as shares FROM portfolio WHERE user_id = ? AND symbol = ? GROUP BY symbol",
                                  user_id, symbol)[0]["shares"]

        if shares > stock_shares:
            return apology("You don't own that many shares", 400)

        # Update user's portfolio and cash
        stock = lookup(symbol)
        total_sale = shares * stock["price"]

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_sale, user_id)
        db.execute("INSERT INTO portfolio (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, -shares, stock["price"])

        # Log the transaction in the transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                   user_id, symbol, -shares, stock["price"])

        return redirect("/")
    else:
        user_id = session["user_id"]
        stocks = db.execute(
            "SELECT symbol FROM portfolio WHERE user_id = ? GROUP BY symbol", user_id)
        return render_template("sell.html", stocks=stocks)


# Login route for existing users
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("must provide username and password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username or password", 400)

        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("login.html")


# Helper functions and routes will be completed as needed for sell, history, etc.

if __name__ == "__main__":
    app.run()
