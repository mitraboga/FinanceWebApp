import urllib.request
import json
import os
from flask import redirect, render_template, request, session
from functools import wraps

def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", message=message), code

def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def lookup(symbol):
    """Look up quote for symbol."""
    try:
        # Contact API
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={api_key}"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode("utf-8"))

        return {
            "symbol": data["symbol"],
            "name": data["companyName"],
            "price": data["latestPrice"]
        }
    except:
        return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
