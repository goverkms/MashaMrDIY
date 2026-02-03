from flask import Flask, render_template_string, request, redirect, url_for, flash
import os
import csv
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'diy_money_secret'

transactions_file = "transactions.csv"
state_file = "state.json"

# --- File initialization ---
def initialize_files():
    if not os.path.exists(transactions_file):
        with open(transactions_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Description", "Amount", "Balance"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d"), "Starting Balance", 0.0, 0.0])
    if not os.path.exists(state_file):
        with open(state_file, 'w') as f:
            json.dump({"last_run_date": datetime.now().strftime("%Y-%m-%d")}, f)

# --- Core logic ---
def get_current_balance():
    if not os.path.exists(transactions_file):
        initialize_files()
    with open(transactions_file, newline='') as file:
        reader = list(csv.reader(file))
        if len(reader) < 2:
            return 0.0
        return float(reader[-1][3])

def add_transaction(description, amount):
    balance = get_current_balance() + amount
    with open(transactions_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d"), description, amount, balance])

def calculate_missed_tuesdays(last_run_date):
    today = datetime.now().date()
    last_date = datetime.strptime(last_run_date, "%Y-%m-%d").date()
    days_passed = (today - last_date).days
    missed = 0
    for i in range(1, days_passed + 1):
        day = last_date + timedelta(days=i)
        if day.weekday() == 1:  # Tuesday
            missed += 1
    return missed

def get_last_run_date():
    with open(state_file) as f:
        state = json.load(f)
    return state.get("last_run_date")

def update_last_run_date():
    with open(state_file, 'w') as f:
        json.dump({"last_run_date": datetime.now().strftime("%Y-%m-%d")}, f)

def update_weekly_allowance():
    last_run_date = get_last_run_date()
    missed_tuesdays = calculate_missed_tuesdays(last_run_date)
    if missed_tuesdays > 0:
        for _ in range(missed_tuesdays):
            add_transaction("Weekly Allowance", 50.00)
    update_last_run_date()
    return missed_tuesdays

def get_transactions():
    if not os.path.exists(transactions_file):
        initialize_files()
    with open(transactions_file, newline='') as file:
        reader = csv.reader(file)
        return list(reader)

# --- Flask routes ---
# PythonAnywhere (Python 3.13) не поддерживает before_first_request, используем инициализацию при каждом запросе
@app.before_request
def before_request_func():
    if not os.path.exists(transactions_file) or not os.path.exists(state_file):
        initialize_files()
    update_weekly_allowance()

@app.route('/')
def index():
    balance = get_current_balance()
    return render_template_string('''
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
      .container { max-width: 540px; margin: 0 auto; padding: 24px; }
      h2 { font-size: 2.2em; margin-bottom: 32px; }
      .menu-col { display: flex; flex-direction: column; gap: 18px; align-items: stretch; margin-top: 32px; }
      .menu-col a { font-size: 1.4em; padding: 18px 0; border-radius: 10px; background: #1cb0e6; color: #fff; text-align: center; text-decoration: none; box-shadow: 0 2px 8px #0001; transition: background 0.2s; }
      .menu-col a:hover { background: #188db3; }
      @media (max-width: 600px) {
        .container { padding: 8px; }
        h2 { font-size: 1.3em; }
        .menu-col a { font-size: 1.1em; padding: 12px 0; }
      }
    </style>
    <div class="container">
    <h2>Current Balance: ${{ balance|round(2) }}</h2>
    <div class="menu-col">
      <a href="{{ url_for('transactions') }}">Transaction History</a>
      <a href="{{ url_for('add') }}">Add/Subtract Money</a>
      <a href="{{ url_for('update_allowance') }}">Update Weekly Allowance</a>
    </div>
    </div>
    ''', balance=balance)

@app.route('/transactions')
def transactions():
    txs = get_transactions()
    return render_template_string('''
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
      .container { max-width: 540px; margin: 0 auto; padding: 24px; }
      h2 { font-size: 2.2em; margin-bottom: 32px; }
      a { display: block; margin: 24px 0 0 0; font-size: 1.2em; padding: 12px 0; border-radius: 10px; text-align: center; background: #eee; color: #222; text-decoration: none; }
      table { width: 100%; font-size: 1.2em; border-collapse: collapse; margin-top: 16px; }
      td, th { padding: 12px; border: 1px solid #ccc; }
      @media (max-width: 600px) {
        .container { padding: 8px; }
        h2 { font-size: 1.3em; }
        table, td, th { font-size: 1em; padding: 7px; }
      }
    </style>
    <div class="container">
    <h2>Transaction History</h2>
    <table>
    {% for row in txs %}
      <tr>{% for x in row %}<td>{{x}}</td>{% endfor %}</tr>
    {% endfor %}
    </table>
    <a href="{{url_for('index')}}">Back</a>
    </div>
    ''', txs=txs)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        desc = request.form.get('desc', '').strip()
        try:
            amt = float(request.form.get('amt', '0'))
            add_transaction(desc, amt)
            flash('Transaction added!')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error: {e}')
    return render_template_string('''
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
      .container { max-width: 540px; margin: 0 auto; padding: 24px; }
      h2 { font-size: 2.2em; margin-bottom: 32px; }
      a, button, input[type=submit] { display: block; width: 100%; margin: 18px 0 0 0; font-size: 1.3em; padding: 14px 0; border-radius: 10px; text-decoration: none; background: #1cb0e6; color: #fff; border: none; text-align: center; }
      a { background: #eee; color: #222; }
      form { margin-top: 12px; }
      input[type=text], input[type=number] { width: 100%; padding: 14px; margin: 10px 0; border-radius: 6px; border: 1px solid #ccc; font-size: 1.2em; }
      {% raw %}@media (max-width: 600px) {
        .container { padding: 8px; }
        h2 { font-size: 1.3em; }
        input[type=text], input[type=number] { font-size: 1em; padding: 8px; }
        a, button, input[type=submit] { font-size: 1em; padding: 10px 0; }
      }{% endraw %}
    </style>
    <div class="container">
    <h2>Add/Subtract Money</h2>
    <form method="post">
      Description: <input name="desc" required type="text"><br>
      Amount: <input name="amt" required type="number" step="0.01"> (use negative for subtract)<br>
      <input type="submit" value="Add">
    </form>
    <a href="{{url_for('index')}}">Back</a>
    {% with messages = get_flashed_messages() %}
      {% if messages %}<ul>{% for m in messages %}<li>{{m}}</li>{% endfor %}</ul>{% endif %}
    {% endwith %}
    </div>
    ''')

@app.route('/update_allowance')
def update_allowance():
    missed = update_weekly_allowance()
    flash(f"Missed Tuesdays (allowances added): {missed}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Do NOT call app.run() on PythonAnywhere
    pass
