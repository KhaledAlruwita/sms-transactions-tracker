from flask import Flask, request, jsonify, render_template_string, make_response
import pandas as pd  
import sqlite3
import subprocess
import requests

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # this to ensure arabic text is written correctly

# store parsed data
data = []


def parse_transaction_message(message):
    transaction_data = {
        "Transaction Type": None,
        "Card Info": None,
        "Amount (SAR)": None,
        "Vendor": None,
        "Year": None,
        "Month": None,
        "Day": None,
        "Time": None,
    }

    for line in message.split("\n"):
        if "شراء" in line:
            transaction_data["Transaction Type"] = line.strip()
        elif "بطاقة:" in line:
            transaction_data["Card Info"] = line.split("بطاقة:")[1].strip()
        elif "مبلغ:" in line:
            amount_part = line.split("مبلغ:")[1].strip()
            transaction_data["Amount (SAR)"] = int(amount_part.replace("SAR", "").strip())
        elif "لدى:" in line:
            transaction_data["Vendor"] = line.split("لدى:")[1].strip()
        elif "في:" in line:
            date_time = line.split("في:")[1].strip()
            date_part, time_part = date_time.split(" ")
            year, month, day = map(int, date_part.split("-"))
            transaction_data["Year"] = year
            transaction_data["Month"] = month
            transaction_data["Day"] = day
            transaction_data["Time"] = time_part.strip()

    return transaction_data

# Route to the HTML form
@app.route('/')
def home():
    html = """
    <!doctype html>
    <html lang="en">
    <head>
        <title>input</title>
    </head>
    <body>
        <h1>Transactions</h1>
        <form action="/chat" method="post">
            <textarea name="message" rows="6" cols="50" placeholder="paste transaction details here"></textarea><br><br>
            <button type="submit">Submit</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

# Route to handle form 
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('message', '')  # Get message from the form
    parsed_info = parse_transaction_message(user_input)

    if parsed_info["Transaction Type"]:
        try:
            # store data in the SQLite db
            conn = sqlite3.connect('transactions.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (transaction_type, card_info, amount, vendor, year, month, day, time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                parsed_info["Transaction Type"],
                parsed_info["Card Info"],
                parsed_info["Amount (SAR)"],
                parsed_info["Vendor"],
                parsed_info["Year"],
                parsed_info["Month"],
                parsed_info["Day"],
                parsed_info["Time"]
            ))
            conn.commit()
            conn.close()

            response_html = f"""
            <!doctype html>
            <html lang="en">
            <head>
                <title>Response</title>
            </head>
            <body>
                <h1>Parsed Info</h1>
                <ul>
                    <li>Transaction Type: {parsed_info["Transaction Type"]}</li>
                    <li>Card Info: {parsed_info["Card Info"]}</li>
                    <li>Amount (SAR): {parsed_info["Amount (SAR)"]}</li>
                    <li>Vendor: {parsed_info["Vendor"]}</li>
                    <li>Year: {parsed_info["Year"]}</li>
                    <li>Month: {parsed_info["Month"]}</li>
                    <li>Day: {parsed_info["Day"]}</li>
                    <li>Time: {parsed_info["Time"]}</li>
                </ul>
                <br>
                <a href="/">Back to Home</a>
            </body>
            </html>
            """
            return response_html
        except sqlite3.IntegrityError:
            #
            return "This transaction already exists in the db. <a href='/'>Try again</a>"
    else:
        return "the msg format maybe not supported yet... <a href='/'>Try again</a>"

@app.route('/transactions', methods=['GET'])
def view_transactions():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions')
    rows = cursor.fetchall()
    conn.close()

    transactions_html = """
    <!doctype html>
    <html lang="en">
    <head>
        <title>Stored Transactions </title>
    </head>
    <body>
        <h1>Stored Transactions db:</h1>
        <table border="1">
            <tr>
                <th>ID</th>
                <th>Transaction Type</th>
                <th>Card Info</th>
                <th>Amount (SAR)</th>
                <th>Vendor</th>
                <th>Year</th>
                <th>Month</th>
                <th>Day</th>
                <th>Time</th>
            </tr>
    """
    for row in rows:
        transactions_html += f"""
            <tr>
                <td>{row[0]}</td>
                <td>{row[1]}</td>
                <td>{row[2]}</td>
                <td>{row[3]}</td>
                <td>{row[4]}</td>
                <td>{row[5]}</td>
                <td>{row[6]}</td>
                <td>{row[7]}</td>
                <td>{row[8]}</td>
            </tr>
        """
    transactions_html += """
        </table>
        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """
    return transactions_html

# create sql db
def init_db():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT,
            card_info TEXT,
            amount INTEGER,
            vendor TEXT,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            time TEXT,
            UNIQUE(transaction_type, card_info, amount, vendor, year, month, day, time)
        )
    ''')
    conn.commit()
    # Enable WAL 
    cursor.execute('PRAGMA journal_mode=WAL;')
    conn.commit()
    conn.close()


# Call the init_db function when the app starts
init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

