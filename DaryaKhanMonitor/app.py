import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import pandas as pd
from twilio.rest import Client
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx', 'xls'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE = 'attendance.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            class TEXT NOT NULL,
            section TEXT NOT NULL,
            parent_name TEXT NOT NULL,
            parent_contact TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id),
            UNIQUE(student_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM students')
    student_count = cursor.fetchone()['count']
    conn.close()
    return render_template('index.html', student_count=student_count)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                else:
                    df = pd.read_excel(filepath)
                
                required_columns = ['name', 'roll_number', 'class', 'section', 'parent_name', 'parent_contact']
                if not all(col in df.columns for col in required_columns):
                    flash(f'File must contain columns: {", ".join(required_columns)}', 'error')
                    os.remove(filepath)
                    return redirect(request.url)
                
                conn = get_db()
                cursor = conn.cursor()
                
                success_count = 0
                update_count = 0
                error_count = 0
                
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                            INSERT INTO students (name, roll_number, class, section, parent_name, parent_contact)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (str(row['name']), str(row['roll_number']), str(row['class']), 
                              str(row['section']), str(row['parent_name']), str(row['parent_contact'])))
                        success_count += 1
                    except sqlite3.IntegrityError:
                        cursor.execute('''
                            UPDATE students 
                            SET name=?, class=?, section=?, parent_name=?, parent_contact=?
                            WHERE roll_number=?
                        ''', (str(row['name']), str(row['class']), str(row['section']), 
                              str(row['parent_name']), str(row['parent_contact']), str(row['roll_number'])))
                        update_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error processing row: {e}")
                
                conn.commit()
                conn.close()
                os.remove(filepath)
                
                flash(f'Successfully added {success_count} students, updated {update_count} students. Errors: {error_count}', 'success')
                return redirect(url_for('students'))
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload CSV or Excel file.', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/students')
def students():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT class FROM students ORDER BY class')
    classes = [row['class'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT section FROM students ORDER BY section')
    sections = [row['section'] for row in cursor.fetchall()]
    
    class_filter = request.args.get('class', '')
    section_filter = request.args.get('section', '')
    
    query = 'SELECT * FROM students WHERE 1=1'
    params = []
    
    if class_filter:
        query += ' AND class = ?'
        params.append(class_filter)
    
    if section_filter:
        query += ' AND section = ?'
        params.append(section_filter)
    
    query += ' ORDER BY class, section, roll_number'
    
    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()
    
    return render_template('students.html', students=students, classes=classes, sections=sections, 
                         class_filter=class_filter, section_filter=section_filter)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        date = request.form.get('date')
        attendance_data = request.form.getlist('attendance')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM students')
        all_students = [row['id'] for row in cursor.fetchall()]
        
        for student_id in all_students:
            status = 'present' if str(student_id) in attendance_data else 'absent'
            
            try:
                cursor.execute('''
                    INSERT INTO attendance (student_id, date, status)
                    VALUES (?, ?, ?)
                ''', (student_id, date, status))
            except sqlite3.IntegrityError:
                cursor.execute('''
                    UPDATE attendance 
                    SET status = ?
                    WHERE student_id = ? AND date = ?
                ''', (status, student_id, date))
        
        conn.commit()
        conn.close()
        
        flash(f'Attendance for {date} has been saved successfully', 'success')
        return redirect(url_for('attendance'))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    class_filter = request.args.get('class', '')
    section_filter = request.args.get('section', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT class FROM students ORDER BY class')
    classes = [row['class'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT section FROM students ORDER BY section')
    sections = [row['section'] for row in cursor.fetchall()]
    
    query = '''
        SELECT s.*, a.status
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
        WHERE 1=1
    '''
    params = [date]
    
    if class_filter:
        query += ' AND s.class = ?'
        params.append(class_filter)
    
    if section_filter:
        query += ' AND s.section = ?'
        params.append(section_filter)
    
    query += ' ORDER BY s.class, s.section, s.roll_number'
    
    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()
    
    return render_template('attendance.html', students=students, date=date, classes=classes, 
                         sections=sections, class_filter=class_filter, section_filter=section_filter)

@app.route('/records')
def records():
    date_filter = request.args.get('date', '')
    class_filter = request.args.get('class', '')
    section_filter = request.args.get('section', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT class FROM students ORDER BY class')
    classes = [row['class'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT section FROM students ORDER BY section')
    sections = [row['section'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT date FROM attendance ORDER BY date DESC')
    dates = [row['date'] for row in cursor.fetchall()]
    
    query = '''
        SELECT s.name, s.roll_number, s.class, s.section, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    '''
    params = []
    
    if date_filter:
        query += ' AND a.date = ?'
        params.append(date_filter)
    
    if class_filter:
        query += ' AND s.class = ?'
        params.append(class_filter)
    
    if section_filter:
        query += ' AND s.section = ?'
        params.append(section_filter)
    
    query += ' ORDER BY a.date DESC, s.class, s.section, s.roll_number'
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    
    return render_template('records.html', records=records, dates=dates, classes=classes, 
                         sections=sections, date_filter=date_filter, class_filter=class_filter, 
                         section_filter=section_filter)

@app.route('/sms', methods=['GET', 'POST'])
def sms():
    if request.method == 'POST':
        date = request.form.get('date')
        selected_students = request.form.getlist('students')
        
        if not selected_students:
            flash('Please select at least one student', 'error')
            return redirect(request.url)
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, twilio_number]):
            flash('Twilio credentials not configured. Please add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER to environment variables.', 'error')
            return redirect(request.url)
        
        conn = get_db()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        
        try:
            client = Client(account_sid, auth_token)
            
            for student_id in selected_students:
                cursor.execute('''
                    SELECT s.name, s.parent_contact, s.class, s.section
                    FROM students s
                    WHERE s.id = ?
                ''', (student_id,))
                student = cursor.fetchone()
                
                if student:
                    message_body = f"Dear Parent, your child {student['name']} (Class {student['class']}-{student['section']}) was absent on {date}. - Govt. High School Darya Khan"
                    
                    try:
                        parent_contact = student['parent_contact'].strip()
                        if not parent_contact.startswith('+'):
                            parent_contact = '+92' + parent_contact.lstrip('0')
                        
                        message = client.messages.create(
                            body=message_body,
                            from_=twilio_number,
                            to=parent_contact
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Error sending SMS to {student['name']}: {e}")
            
            conn.close()
            flash(f'SMS sent successfully to {success_count} parents. Errors: {error_count}', 'success')
            
        except Exception as e:
            conn.close()
            flash(f'Error sending SMS: {str(e)}', 'error')
        
        return redirect(url_for('sms'))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    class_filter = request.args.get('class', '')
    section_filter = request.args.get('section', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT class FROM students ORDER BY class')
    classes = [row['class'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT section FROM students ORDER BY section')
    sections = [row['section'] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT date FROM attendance ORDER BY date DESC')
    dates = [row['date'] for row in cursor.fetchall()]
    
    query = '''
        SELECT s.id, s.name, s.roll_number, s.class, s.section, s.parent_name, s.parent_contact
        FROM students s
        JOIN attendance a ON s.id = a.student_id
        WHERE a.date = ? AND a.status = 'absent'
    '''
    params = [date]
    
    if class_filter:
        query += ' AND s.class = ?'
        params.append(class_filter)
    
    if section_filter:
        query += ' AND s.section = ?'
        params.append(section_filter)
    
    query += ' ORDER BY s.class, s.section, s.roll_number'
    
    cursor.execute(query, params)
    absent_students = cursor.fetchall()
    conn.close()
    
    return render_template('sms.html', students=absent_students, dates=dates, date=date, 
                         classes=classes, sections=sections, class_filter=class_filter, 
                         section_filter=section_filter)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
