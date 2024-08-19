from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import db, User, Purchase
import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # Query purchases
    purchases_today = Purchase.query.filter_by(owner=user, date=today).all()
    purchases_month = Purchase.query.filter(Purchase.owner == user, Purchase.date >= month_start).all()
    purchases_year = Purchase.query.filter(Purchase.owner == user, Purchase.date >= year_start).all()
    purchases_all_time = Purchase.query.filter_by(owner=user).all()

    def calculate_total(purchases):
        types = [
            'food & necessities', 'hygiene', 'rent & bills', 'gym', 'sada9a',
            'meds', 'transport', 'mobile credits', 'education', 'textile',
            'electronics', 'extra', 'docs', 'meuble', 'waste'
        ]
        stats = {type: 0 for type in types}
        for purchase in purchases:
            stats[purchase.type] += purchase.price
        return stats

    stats_today = calculate_total(purchases_today)
    stats_month = calculate_total(purchases_month)
    stats_year = calculate_total(purchases_year)
    stats_all_time = calculate_total(purchases_all_time)

    def calculate_total_amount(stats):
        return sum(stats.values())

    total_today = calculate_total_amount(stats_today)
    total_month = calculate_total_amount(stats_month)
    total_year = calculate_total_amount(stats_year)
    total_all_time = calculate_total_amount(stats_all_time)

    # Get the date of the oldest entry for 'All Time Purchases'
    oldest_entry = Purchase.query.filter_by(owner=user).order_by(Purchase.date.asc()).first()
    oldest_entry_date = oldest_entry.date if oldest_entry else None

    # Calculate the total sum of all purchases for each month
    purchases_by_month = db.session.query(
        db.func.strftime('%Y-%m', Purchase.date).label('month'),
        db.func.sum(Purchase.price).label('total')
    ).filter_by(owner=user).group_by('month').order_by('month').all()

    # Format the monthly totals for Google Charts
    monthly_totals = {month: total for month, total in purchases_by_month}

    if request.method == 'POST':
        if 'clear_today' in request.form:
            # Clear all today's purchases
            Purchase.query.filter_by(owner=user, date=today).delete()
            db.session.commit()
            return redirect(url_for('index'))
        elif 'add_purchase' in request.form:
            # Add a new purchase directly from the home page
            name = request.form['name']
            price = float(request.form['price'].replace(',', '.'))  # Handle floating-point numbers
            purchase_type = request.form['type']
            new_purchase = Purchase(name=name, price=price, type=purchase_type, owner=user)
            db.session.add(new_purchase)
            db.session.commit()
            return redirect(url_for('index'))

    # Pass the current month, year, and oldest entry date to the template
    current_month = today.strftime("%B")
    current_year = today.year

    return render_template(
        'home.html',
        stats_today=stats_today,
        stats_month=stats_month,
        stats_year=stats_year,
        stats_all_time=stats_all_time,
        total_today=total_today,
        total_month=total_month,
        total_year=total_year,
        total_all_time=total_all_time,
        current_month=current_month,
        current_year=current_year,
        oldest_entry_date=oldest_entry_date,
        monthly_totals=monthly_totals  # Pass monthly totals to the template
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
