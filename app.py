import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g

app = Flask(__name__)
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        # Table for Items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                rate REAL NOT NULL
            )
        ''')
        # Table for Bills
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institute_name TEXT NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT NOT NULL,
                cheque_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Table for Bill Line Items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER,
                item_name TEXT,
                unit TEXT,
                rate REAL,
                quantity REAL,
                amount REAL,
                FOREIGN KEY (bill_id) REFERENCES bills (id)
            )
        ''')
        db.commit()

# --- ROUTES ---

@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM bills ORDER BY id DESC')
    bills = cursor.fetchall()
    return render_template('index.html', bills=bills)

@app.route('/items', methods=['GET', 'POST'])
def items():
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        name = request.form['name']
        unit = request.form['unit']
        rate = float(request.form['rate'])
        cursor.execute('INSERT INTO items (name, unit, rate) VALUES (?, ?, ?)', (name, unit, rate))
        db.commit()
        return redirect(url_for('items'))
    
    cursor.execute('SELECT * FROM items')
    all_items = cursor.fetchall()
    return render_template('items.html', items=all_items)

@app.route('/items/delete/<int:item_id>')
def delete_item(item_id):
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (item_id,))
    db.commit()
    return redirect(url_for('items'))

@app.route('/create-bill', methods=['GET', 'POST'])
def create_bill():
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        institute_name = request.form['institute_name']
        status = request.form['status']
        cheque_note = request.form['cheque_note']
        
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        total_amount = 0.0
        bill_items_to_insert = []
        
        for item_id, qty in zip(item_ids, quantities):
            if qty and float(qty) > 0:
                cursor.execute('SELECT * FROM items WHERE id = ?', (item_id,))
                item = cursor.fetchone()
                quantity = float(qty)
                amount = item['rate'] * quantity
                total_amount += amount
                bill_items_to_insert.append((item['name'], item['unit'], item['rate'], quantity, amount))
        
        # Save Bill
        cursor.execute('''
            INSERT INTO bills (institute_name, total_amount, status, cheque_note)
            VALUES (?, ?, ?, ?)
        ''', (institute_name, total_amount, status, cheque_note))
        bill_id = cursor.lastrowid
        
        # Save Bill Items
        for b_item in bill_items_to_insert:
            cursor.execute('''
                INSERT INTO bill_items (bill_id, item_name, unit, rate, quantity, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (bill_id, b_item[0], b_item[1], b_item[2], b_item[3], b_item[4]))
            
        db.commit()
        return redirect(url_for('view_bill', bill_id=bill_id))
        
    cursor.execute('SELECT * FROM items')
    available_items = cursor.fetchall()
    return render_template('create_bill.html', items=available_items)

@app.route('/bill/<int:bill_id>')
def view_bill(bill_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM bills WHERE id = ?', (bill_id,))
    bill = cursor.fetchone()
    
    cursor.execute('SELECT * FROM bill_items WHERE bill_id = ?', (bill_id,))
    items = cursor.fetchall()
    return render_template('view_bill.html', bill=bill, items=items)

@app.route('/bill/update-status/<int:bill_id>', methods=['POST'])
def update_status(bill_id):
    db = get_db()
    status = request.form['status']
    cheque_note = request.form['cheque_note']
    db.execute('UPDATE bills SET status = ?, cheque_note = ? WHERE id = ?', (status, cheque_note, bill_id))
    db.commit()
    return redirect(url_for('view_bill', bill_id=bill_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
