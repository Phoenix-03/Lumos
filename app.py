#imports
from flask import Flask, redirect, render_template, session, flash, request, url_for
import pymongo
from flask_socketio import SocketIO
import random
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import threading
from collections import defaultdict
import time
import logging
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score


#define app and flask
app = Flask(__name__)
app.secret_key = 'supersecretkey'
socketio = SocketIO(app)

# connect with MongoDB
client = pymongo.MongoClient('mongodb+srv://annabethchase120703:wisegirl@cluster0.qbj6po9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.lumos
users_collection = db.users
expenses = db.expenses
budgets = db.budgets

# -------------functions-----------------
# Predefined questions
questions = [
    {'id': 1, 'question': 'What is the capital of France?', 'options': ['Paris', 'London', 'Rome', 'Berlin'], 'correct_answer': 'Paris', 'difficulty': 'easy', 'hint': 'It is known as the city of love.'},
    {'id': 2, 'question': 'What is 2 + 2?', 'options': ['3', '4', '5', '6'], 'correct_answer': '4', 'difficulty': 'easy', 'hint': 'It is an even number.'},
    {'id': 3, 'question': 'What is the largest planet in our solar system?', 'options': ['Earth', 'Mars', 'Jupiter', 'Saturn'], 'correct_answer': 'Jupiter', 'difficulty': 'medium', 'hint': 'It is named after the king of the Roman gods.'},
    # Add more questions as needed
]

INITIAL_POINTS = 0
HINT_COST = 5

#for quiz
def get_points_for_question(question):
    # Example logic: points based on question difficulty (e.g., easy: 10, medium: 20, hard: 30)
    if question['difficulty'] == 'easy':
        return 10
    elif question['difficulty'] == 'medium':
        return 20
    elif question['difficulty'] == 'hard':
        return 30
    
# two functions for schedule and sending notification of chores
def send_push_notification(chore_name):
    notification_data = {
        'title': 'Reminder',
        'body': f"Remember to complete your chore: {chore_name}",
        'icon': 'static\images\savings.jpeg'
    }
    socketio.emit('notification', notification_data)
    print(f'sending notification for {chore_name}')

def schedule_notification(chore_id, chore_name, notification_time):
    now = datetime.now()
    wait_time = (notification_time - now).total_seconds()
    if wait_time > 0:
        time.sleep(wait_time)
    send_push_notification(chore_name)

# functions for interest of fd and ppf
def calculate_annual_interest(principal, interest_rate):
    annual_interest = principal*interest_rate/100
    return annual_interest

def add_interest_fd(interval = 3600):
    def update_interest():
        fd_accounts_list = list(users_collection.find({'account.fixed_deposits':{'$exists': True}}))

        for user in fd_accounts_list:
            fd_accounts = user.get('account',{}).get('fixed_deposits',[])
            for fd in fd_accounts:
                principal = fd['balance']
                interest_rate = fd['interest_rate']
                interest = calculate_annual_interest(principal,interest_rate)

                fd['balance'] += interest
                fd['transactions'].append({
                    'date': datetime.now().strftime('%d-%m-%Y'),
                    'type': 'interest',
                    'amount': interest
                })

                users_collection.update_one({'_id': user['_id']}, {'$set': {'account.fixed_deposits': fd_accounts}})
    
    update_interest()

    threading.Timer(interval, add_interest_fd, [interval]).start()

add_interest_fd()

def add_interest_ppf(interval = 43200):
    def update_interest():
        ppf_accounts_list = list(users_collection.find({'account.ppf':{'$exists': True}}))

        for user in ppf_accounts_list:
            ppf_accounts = user.get('account',{}).get('ppf',[])
            for ppf in ppf_accounts:
                principal = ppf['balance']
                interest_rate = ppf['interest_rate']
                interest = calculate_annual_interest(principal,interest_rate)

                ppf['balance'] += interest
                ppf['transactions'].append({
                    'date': datetime.now().strftime('%d-%m-%Y'),
                    'type': 'interest',
                    'amount': interest
                })

                users_collection.update_one({'_id': user['_id']}, {'$set': {'account.ppf': ppf_accounts}})

                print('successfull')
    
    update_interest()

    threading.Timer(interval, add_interest_ppf, [interval]).start()

add_interest_ppf()

# --------------------------routes------------------------------

# landing page
@app.route('/')
def landing():
    return render_template('landing.html')

# register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        dob = request.form.get('dob')
        gender = request.form.get('gender')

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        
        cvv = random.randint(100, 999)
        date = datetime.now().strftime('%d-%m-%Y')

        # age = date - dob

        user = {
            'username': username,
            'password': password,
            'dob': dob,
            'gender': gender,
            # 'age': age,
            'account': {
                'savings': {
                    'account_number': random.randint(100000000000, 999999999999),
                    'balance': 1000.0,
                    'cvv': cvv,
                    'name': username,
                    'account_creation_date': date,
                    'bank_name': 'CASHE',
                    'ifsc_code': 'CASHE000123',
                    'transactions': [
                        {'amount': '1000.0', 'type': 'credit', 'date': date, 'reason': 'Initial credit from Lumos'}
                    ]
                }
            }   
        }

        users_collection.insert_one(user)
        flash('Registeration Successful')

        return redirect(url_for('login'))
    
    return render_template('register.html')

# login
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = users_collection.find_one({'username':username})

        if user and user['password'] == password:
            session['user_id'] = str(user['_id'])
            flash("Login Successful!")
            return redirect(url_for('mhome'))
        else:
            flash("Invalid Username or Password")
            return redirect(url_for('login'))
        
    return render_template('login.html')

# home
@app.route('/mhome')
def mhome():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    
    return render_template('home.html', username = username, tpoints = savings_account['balance'])
    

# -------------bank-----------------

# bank index
@app.route('/bank')
def bank_index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')

    return render_template('bank_index.html', tpoints = savings_account['balance'], username = user['username'])

# savings
@app.route('/savings')
def savings():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')

    return render_template('savings.html', tpoints = savings_account['balance'], username = user['username'], savings_account=savings_account)

# fd
@app.route('/fixed_deposit', methods=['GET', 'POST'])
def fixed_deposit():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')

    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        interest_rate = 5.0
        maturity_period = int(request.form.get('maturity_period'))
        maturity_date = datetime.now() + timedelta(days=maturity_period)
        date = datetime.now()

        if amount <= savings_account['balance']:
            fd_account = {
                'principal_amount': amount,
                'interest_rate': interest_rate,
                'maturity_date': maturity_date.strftime('%d-%m-%Y'),
                'account_number': f"FD{random.randint(10000000,99999999)}",
                'balance': amount,
                'transactions': [
                    {'amount': amount, 'date': date.strftime('%d-%m-%Y'), 'type':'credit'}
                ]
            }

            users_collection.update_one({"_id": ObjectId(user_id)}, {'$push': {'account.fixed_deposits': fd_account}})

            savings_account['balance'] -= amount
            savings_account['transactions'].append({
                'amount': amount,
                'type': 'debit',
                'date': date.strftime('%d-%m-%Y'),
                'reason': 'Transferred to FD: ' + fd_account['account_number']
            })

            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings': savings_account}})

            return redirect(url_for('fixed_deposit'))
        else:
            return 'Insufficient balance'

    fd_accounts = user.get('account',{}).get('fixed_deposits', [])
    return render_template('fixed_deposit.html', fd_accounts = fd_accounts, tpoints = savings_account['balance'], username = user['username'])

# fd details
@app.route('/fixed_deposit/<account_number>')
def fixed_deposit_detail(account_number):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    fd_accounts = user.get('account', {}).get('fixed_deposits', [])
    fd_account = next((fd for fd in fd_accounts if fd['account_number'] == account_number), None)

    if not fd_account:
        return 'FD not found'
    
    savings_account = user.get('account', {}).get('savings')

    return render_template('fixed_deposit_detail.html', fd_account=fd_account, tpoints = savings_account['balance'], username = user['username'])

# ppf
@app.route('/ppf', methods=['GET', 'POST'])
def ppf():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')

    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        interest_rate = 7.1
        maturity_period = 45
        maturity_date = datetime.now() + timedelta(days=maturity_period)
        date = datetime.now()

        if amount <= savings_account['balance']:
            ppf_account = {
                'principal_amount': amount,
                'interest_rate': interest_rate,
                'maturity_date': maturity_date.strftime('%d-%m-%Y'),
                'account_number': f"PPF{random.randint(10000000,99999999)}",
                'balance': amount,
                'transactions': [
                    {'amount': amount, 'date': date.strftime('%d-%m-%Y'), 'type':'credit'}
                ]
            }

            users_collection.update_one({"_id": ObjectId(user_id)}, {'$push': {'account.ppf': ppf_account}})

            savings_account['balance'] -= amount
            savings_account['transactions'].append({
                'amount': amount,
                'type': 'debit',
                'date': date.strftime('%d-%m-%Y'),
                'reason': 'Transferred to PPF: ' + ppf_account['account_number']
            })

            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings': savings_account}})

            return redirect(url_for('ppf'))
        else:
            return 'Insufficient balance'

    ppf_account = user.get('account',{}).get('ppf', [])
    return render_template('ppf.html', ppf_account = ppf_account, tpoints = savings_account['balance'], username = user['username'])

# ppf details
@app.route('/ppf/<account_number>')
def ppf_detail(account_number):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    ppf_accounts = user.get('account', {}).get('ppf', [])
    ppf_account = next((ppf for ppf in ppf_accounts if ppf['account_number'] == account_number), None)

    if not ppf_account:
        return 'FD not found'
    
    savings_account = user.get('account', {}).get('savings')

    return render_template('ppf_detail.html', ppf_account=ppf_account, tpoints = savings_account['balance'], username = user['username'])

# transfer
@app.route('/quick_transfer', methods=['GET', 'POST'])
def quick_transfer():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account', {}).get('savings')
    me = savings_account['name']
    my_acc = savings_account['account_number']

    if request.method == 'POST':
        name = request.form.get('name')
        account_number = request.form.get('account_number')
        re_account_number = request.form.get('re_account_number')
        ifsc_code = request.form.get('ifsc_code')
        amount = float(request.form.get('amount'))
        purpose = request.form.get('purpose')
        date = datetime.now()

        if account_number != re_account_number:
            return 'Account numbers do not match'
        
        if amount <= savings_account['balance']:
            # Check if transfer is to user's own PPF account
            ppf_accounts = user.get('account', {}).get('ppf', [])
            ppf_account = next((ppf for ppf in ppf_accounts if ppf['account_number'] == account_number), None)
            if ppf_account and ifsc_code == savings_account['ifsc_code']:
                ppf_account['balance'] += amount
                ppf_account['transactions'].append({
                    'amount': amount,
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'credit'
                })
                flash("Successfully Transferred to your PPF account: " + ppf_account['account_number'])
                users_collection.update_one({'_id': user['_id']}, {'$set': {'account.ppf': ppf_accounts}})

            else:
                # Check if transfer is to another user's savings account
                target_user = users_collection.find_one({'username': name})
                if target_user:
                    target_savings_account = target_user['account']['savings']
                    target_savings_account['balance'] += amount
                    target_savings_account['transactions'].append({
                        'amount': amount,
                        'date': date.strftime('%Y-%m-%d'),
                        'type': 'credit',
                        'reason': f'Transferred from {me} {my_acc}'
                    })
                    users_collection.update_one({'_id': target_user['_id']}, {'$set': {'account.savings': target_savings_account}})
                    flash("Successfully Transferred to account number: " + account_number)
                else:
                    return 'Invalid target account number'

            # Update sender's savings account
            savings_account['balance'] -= amount
            savings_account['transactions'].append({
                'amount': amount,
                'type': 'debit',
                'date': date.strftime('%Y-%m-%d'),
                'reason': purpose
            })
            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings': savings_account}})

            return redirect(url_for('savings'))
        else:
            return 'Insufficient balance'
        
    return render_template('quick_transfer.html', username=user['username'], tpoints=savings_account['balance'])



@app.route('/transfer_with_dbcard', methods = ['GET','POST'])
def transfer_with_dbcard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account', {}).get('savings')

    if request.method == 'POST':
        name = request.form.get('cardholderName')
        card_number = request.form.get('cardNumber')
        expiry_date = request.form.get('expiryDate')
        cvv = int(request.form.get('cvv'))
        amount = float(request.form.get('amount'))
        purpose = request.form.get('remarks')
        date = datetime.now()
        month, year = int(expiry_date[:2]), int('20' + expiry_date[3:])  # Assuming the year is in the format YY
        expiry_datetime = datetime(year, month, 1)

        if expiry_datetime < datetime.now():
            return 'Expired Debit Card'
        
        if amount <= savings_account['balance'] and cvv == savings_account['cvv']:    
            ppf_accounts = user.get('account',{}).get('ppf',[])
            for ppf in ppf_accounts:
                ppf['balance'] += amount
                ppf['transactions'].append({
                    'amount': amount,
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'credit'
                })
                flash("Successfully Transfered to " + ppf['account_number'])
                users_collection.update_one({'_id': user['_id']}, {'$set': {'account.ppf': ppf_accounts}})

            savings_account['balance'] -= amount
            savings_account['transactions'].append({
                'amount' : amount,
                'type': 'debit',
                'date': date.strftime('%Y-%m-%d'),
                'reason': purpose
            })
            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings':savings_account}})

            return redirect(url_for('savings'))
        else:
            return 'Insufficient balance'
        
    return render_template('transfer_with_dbcard.html', username=user['username'], tpoints=savings_account['balance'])

# -------------chore-----------------

# chore index
@app.route('/chore_index')
def chore_index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    chores = user.get('chores',[])

    chores_by_day = defaultdict(list)
    for chore in chores:
        day = chore['date'].strftime('%A, %d-%m-%Y')
        chores_by_day[day].append(chore)

    savings_account = user.get('account',{}).get('savings')

    return render_template('chore_index.html', tpoints = savings_account['balance'], chores_by_day = chores_by_day, username = user['username'])

# add chore
@app.route('/add_chore', methods=['GET', 'POST'])
def add_chore():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')

    if request.method == 'POST':
        notification_time = request.form.get('notification_time')
        if notification_time:
            notification_time = datetime.strptime(notification_time, '%Y-%m-%dT%H:%M')
        else:
            notification_time = datetime.now() + timedelta(minutes=2)

        chore= {
            '_id': ObjectId(),
            'name': request.form.get('name'),
            'completed': False,
            'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d') if request.form.get('date') else datetime.now(),
            'points': 10,
            'notification_time': notification_time
        }

        users_collection.update_one({'_id': ObjectId(user_id)}, {"$push":{"chores":chore}})

        threading.Thread(target=schedule_notification, args=(str(chore['_id']), chore['name'], chore['notification_time'])).start()
        
        return redirect(url_for('chore_index'))
    
    return render_template('add_chore.html', tpoints = savings_account['balance'], username = user['username'])


# complete chore
@app.route('/complete_chore/<chore_id>')
def complete_chore(chore_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')
    chores = user.get('chores',[])

    for chore in chores:
        if str(chore['_id']) == chore_id and not chore['completed']:
            chore['completed'] = True
            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set':{'chores': chores}})

            savings_account['balance'] += chore['points']
            savings_account['transactions'].append({
                'amount': chore['points'],
                'type': 'credit',
                'date' : datetime.now().strftime('%d-%m-%Y'),
                'reason': 'Points Added from Chore: ' + chore['name']
            })
            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings':savings_account}})

    return redirect(url_for('chore_index'))        

# delete chore
@app.route('/delete_chore/<chore_id>')
def delete_chore(chore_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$pull': {'chores': {'_id': ObjectId(chore_id)}}})
    return redirect(url_for('chore_index'))

# edit chore
@app.route('/edit_chore/<chore_id>', methods=['GET', 'POST'])
def edit_chore(chore_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    chores = user.get('chores', [])
    chore = next((ch for ch in chores if str(ch['_id']) == chore_id ),None)

    if request.method == 'POST':
        notification_time = request.form.get('notification_time')
        if notification_time:
            notification_time = datetime.strptime(notification_time, '%Y-%m-%dT%H:%M')
        else:
            notification_time = chore['notification_time']

        updated_chore = {
            'name': request.form.get('name'),
            'notification_time': notification_time,
            'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d') if request.form.get('date') else chore['date']
        }

        for ch in chore:
            if str(ch['_id']) == chore_id:
                ch.update(updated_chore)
                break

        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'chores':chores}})
        return redirect(url_for('chore_index'))
    
    savings_account = user.get('account',{}).get('savings')

    return render_template('edit_chore.html', chore=chore, tpoints = savings_account['balance'], username = user['username'])

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')


# -------------tracker-----------------

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    error_message = None
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account',{}).get('savings')
    

    if request.method == 'POST':
        if 'amount' in request.form and 'category' in request.form:
            # Add expense functionality
            try:
                amount = float(request.form['amount'])
                category = request.form['category']
                date = datetime.now()
                expenses.insert_one({'amount': amount, 'category': category, 'date': date, 'user_id': user_id})
                return redirect(url_for('home'))
            except Exception as e:
                error_message = f"Error adding expense: {str(e)}"

        elif 'budget' in request.form:
            # Set monthly budget functionality
            try:
                budget = float(request.form['budget'])
                month = datetime.now().strftime('%Y-%m')
                budgets.update_one(
                    {'month': month, 'user_id': user_id},
                    {'$set': {'budget': budget}},
                    upsert=True
                )
                return redirect(url_for('home'))
            except Exception as e:
                error_message = f"Error setting budget: {str(e)}"

    try:
        # View monthly expenses functionality
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$date"}},
                "expenses": {"$push": {"_id": "$_id", "date": "$date", "amount": "$amount", "category": "$category"}}
            }},
            {"$sort": {"_id": 1}}
        ]
        monthly_expenses = list(expenses.aggregate(pipeline))

        # Convert date strings to formatted strings
        for month_entry in monthly_expenses:
            for entry in month_entry['expenses']:
                entry['date'] = entry['date'].strftime('%d-%m-%Y')

        # Calculate total expenses
        total_expenses = sum(entry['amount'] for month in monthly_expenses for entry in month['expenses'])

        # Get the budget for the current month
        month = datetime.now().strftime('%Y-%m')
        budget_doc = budgets.find_one({'month': month, 'user_id': user_id})
        budget = budget_doc['budget'] if budget_doc else 0.0

        # Calculate savings
        savings = budget - total_expenses

        return render_template('index.html', monthly_expenses=monthly_expenses, total_expenses=total_expenses, budget=budget, savings=savings, error_message=error_message, user_id=user_id, username = user['username'], tpoints = savings_account['balance'])

    except Exception as e:
        error_message = f"Error fetching expenses: {str(e)}"
        return render_template('index.html', error_message=error_message)

@app.route('/delete_expense/<expense_id>', methods=['GET', 'POST'])
def delete_expense(expense_id):
    try:
        result = expenses.delete_one({'_id': ObjectId(expense_id), 'user_id': session['user_id']})
        if result.deleted_count == 1:
            print(f"Successfully deleted expense with id {expense_id}")
        else:
            print(f"No expense found with id {expense_id}")
    except Exception as e:
        print(f"Error deleting expense: {str(e)}")

    return redirect(url_for('home'))

@app.route('/edit_expense/<expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    try:
        expense = expenses.find_one({'_id': ObjectId(expense_id), 'user_id': session['user_id']})
        if request.method == 'POST':
            updated_expense = {
                'amount': float(request.form.get('amount')),
                'category': request.form.get('category'),
                'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d') if request.form.get('date') else expense['date'],
            }
            expenses.update_one({'_id': ObjectId(expense_id)}, {'$set': updated_expense})
            return redirect(url_for('home'))
        return render_template('edit_expense.html', expense=expense, username=username, tpoints = savings_account['balance'])
    except Exception as e:
        logging.error(f"Error editing expense: {e}")
        return "An error occurred while editing the expense."
    


# -------------reccommendation-----------------

# Load the dataset
df = pd.read_csv('investment_recommendations_10000.csv')

# Encode categorical variables
le_individual_goals = LabelEncoder()
le_gender = LabelEncoder()
le_risk_tolerance = LabelEncoder()
le_financial_literacy = LabelEncoder()
le_recommendations = LabelEncoder()

df['Individual Goals'] = le_individual_goals.fit_transform(df['Individual Goals'])
df['Gender'] = le_gender.fit_transform(df['Gender'])
df['Risk Tolerance'] = le_risk_tolerance.fit_transform(df['Risk Tolerance'])
df['Financial Literacy'] = le_financial_literacy.fit_transform(df['Financial Literacy'])
df['Recommended Investment Products'] = le_recommendations.fit_transform(df['Recommended Investment Products'])

# Features and target variables
X = df[['Individual Goals', 'Age', 'Gender', 'Risk Tolerance', 'Financial Literacy']]
y = df['Recommended Investment Products']

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = DecisionTreeClassifier(random_state=42)
model.fit(X_train, y_train)

# Calculate accuracy
train_accuracy = accuracy_score(y_train, model.predict(X_train))
test_accuracy = accuracy_score(y_test, model.predict(X_test))

print("Model Accuracy:")
print(f"Train Accuracy: {train_accuracy:.2f}")
print(f"Test Accuracy: {test_accuracy:.2f}")

# Function to recommend investment products based on input attributes
def recommend_investment(investment_goals, age, gender, risk_tolerance, financial_literacy):
    # Encode input attributes
    investment_goals_encoded = le_individual_goals.transform([investment_goals])[0]
    gender_encoded = le_gender.transform([gender])[0]
    risk_tolerance_encoded = le_risk_tolerance.transform([risk_tolerance])[0]
    financial_literacy_encoded = le_financial_literacy.transform([financial_literacy])[0]
    
    input_data = [[investment_goals_encoded, age, gender_encoded, risk_tolerance_encoded, financial_literacy_encoded]]

    # Make prediction
    recommendation_encoded = model.predict(input_data)[0]

    # Decode recommendation
    recommendation = le_recommendations.inverse_transform([recommendation_encoded])[0]

    # Assuming recommendations are returned as a comma-separated string
    recommendation_list = recommendation.split(',')

    return recommendation_list

# Flask routes
@app.route('/recomm_home')
def recomm_home():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    return render_template('recomm_index.html', username = username, tpoints = savings_account['balance'])

@app.route('/predict', methods=['POST'])
def predict():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')

    data = request.form
    investment_goals = data['investment_goals']
    age = int(data['age'])
    gender = data['gender']
    risk_tolerance = data['risk_tolerance']
    financial_literacy = data['financial_literacy']
    
    recommendation = recommend_investment(investment_goals, age, gender, risk_tolerance, financial_literacy)
    
    return render_template('recomm_index.html', 
                           investment_goals=investment_goals, 
                           age=age, 
                           gender=gender, 
                           risk_tolerance=risk_tolerance, 
                           financial_literacy=financial_literacy, 
                           recommendation_text=recommendation, 
                           username = username, tpoints = savings_account['balance'])

# -------------games-----------------
@app.route('/games_home')
def games_home():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    return render_template('games_index.html', username = username, tpoints = savings_account['balance'])

#Choices
from story import story

@app.route('/choices_home')
def choices_home():
    scene = story.get_scene('start')
    return render_template('scene.html', scene=scene)

@app.route('/choose', methods=['POST'])
def choose():
    choice = request.form['choice']
    scene = story.get_scene(choice)
    return render_template('scene.html', scene=scene)

#Taxes

question_template = 'Mr. Pandit is {age} years of age. Last year his annual income was Rs. {income}. How much income tax does he have to pay?'

def calculate_tax(age, income):
    if age < 60:
        return int(income * 1)  # 10% tax rate for age less than 60
    elif 60 <= age <= 80:
        return int(income * 0.01)  # 8% tax rate for age between 60 and 80
    else:
        return int(income * 0.001)  # 5% tax rate for age above 80

@app.route('/income', methods=['GET', 'POST'])
def income():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    if request.method == 'POST':
        question_index = int(request.form['question_index'])
        age = int(request.form['age'])
        income = int(request.form['income'])
        show_hint = 'hint' in request.form

        # Generate the current question and answer
        question = question_template.format(age=age, income=income)
        correct_answer = calculate_tax(age, income)  # Calculate correct answer based on age and income

        if 'answer' in request.form:
            answer = request.form.get('answer')

            if answer and answer.isdigit() and int(answer) == correct_answer:
                flash('Correct! Well done. New question loaded.', 'success')
                question_index += 1
                if question_index < 5:
                    # Generate new random values for the next question
                    age = random.randint(17, 100)
                    income = random.randint(50000, 1000000)
                else:
                    flash('Quiz completed!', 'success')
                    return render_template('income_index.html', question=None, show_hint=False, quiz_finished=True, username=username, tpoints = savings_account['balance'])
            else:
                flash('Incorrect. Try again.', 'danger')
    else:
        question_index = 0
        age = random.randint(17, 100)
        income = random.randint(50000, 1000000)
        show_hint = False

    question = question_template.format(age=age, income=income)
    quiz_finished = question_index >= 5

    return render_template('income_index.html', question=question, show_hint=show_hint, quiz_finished=quiz_finished, question_index=question_index, age=age, income=income, username = username, tpoints = savings_account['balance'])

@app.route('/gst', methods=['GET', 'POST'])
def gst():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    return render_template('gst_index.html', username=username, tpoints = savings_account['balance'])


#quiz

@app.route('/quiz_index')
def quiz_index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')
    return render_template('quiz_index.html', username = username, tpoints = savings_account['balance'])


@app.route('/start')
def start_quiz():
    return redirect(url_for('quiz', id=0, points=INITIAL_POINTS, hint_used=False))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    savings_account = user.get('account', {}).get('savings')
    if not savings_account:
        savings_account = {'balance': 0, 'transactions': []}
    
    if request.method == 'POST':
        user_answer = request.form['answer']
        id = int(request.form['id'])
        points = int(request.form['points'])
        hint_used = request.form.get('hint_used') == 'True'

        question = questions[id]

        if question['correct_answer'] == user_answer:
            points += get_points_for_question(question)
        else:
            points -= 5  # Deduct points for incorrect answer

        id += 1

        if id >= len(questions):
            return redirect(url_for('result', points=points))

        return redirect(url_for('quiz', id=id, points=points, hint_used=hint_used))

    id = int(request.args.get('id', 0))
    points = int(request.args.get('points', INITIAL_POINTS))
    hint_used = request.args.get('hint_used') == 'True'
    current_question = questions[id]

    savings_account['balance'] += points
    savings_account['transactions'].append({
        'amount': points,
        'type': 'credit',
        'date': datetime.now().strftime('%d-%m-%Y'),
        'reason': 'From Quiz'
    })

    print(f"Savings account after update: {savings_account}")

    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'account.savings': savings_account}})

    return render_template('quiz.html', question=current_question, id=id, points=points, hint_used=hint_used, username=user['username'], tpoints = savings_account['balance'])


@app.route('/result')
def result():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    username = user['username']
    savings_account = user.get('account',{}).get('savings')

    points = int(request.args.get('points', INITIAL_POINTS))
    return render_template('result.html', points=points, username = username, tpoints = savings_account['balance'])

#start the application

if __name__ == '__main__':
    app.run(debug=True)