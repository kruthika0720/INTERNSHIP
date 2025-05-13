import time
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file, flash
import sqlite3
import glob
import qrcode
import os
import random
import smtplib
import csv
from fpdf import FPDF
import calendar
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

# File Upload Config
UPLOAD_FOLDER = "static/profile_pics"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection

def get_db_connection():
    conn = sqlite3.connect("employees.db")
    conn.row_factory = sqlite3.Row
    return conn

# Load Employee Data from Excel

EMPLOYEE_FILE = "employees.xlsx"

def get_employee_emails():
    """ Read Excel and return a list of employee emails """
    if not os.path.exists(EMPLOYEE_FILE):
        print("Error: employees.xlsx not found!")
        return []
    df = pd.read_excel(EMPLOYEE_FILE)
    return df["email"].tolist()  # Assuming the email column name is 'email'

# Function to generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))
otp_storage = {}  # Store OTP with expiry time


# Route: Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        emp_id = request.form["emp_id"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE emp_id = ? AND password = ?", (emp_id, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session["emp_id"] = emp_id
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Credentials!", "error")
    return render_template("login.html")

# Function to send OTP via Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(receiver_email, otp):
    sender_email = os.getenv("MAIL_USERNAME")
    app_password = os.getenv("MAIL_PASSWORD")

    if not sender_email or not app_password:
        print("Error: Email credentials not set!")
        return False

    subject = "Your OTP Code"
    body = f"Your OTP is: {otp}\n\nThis OTP will expire in 5 minutes."

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Change SMTP to use SSL (Port 465)
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)  
        
        print("Logging in to email...")
        server.login(sender_email, app_password)  
        print("Login successful!")

        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"OTP email sent successfully to {receiver_email}!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP Authentication failed. Check email and password.")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Error sending email: {e}")
    return False

# def send_otp(email, otp):
#     sender_email = "ytclipsfor@gmail.com"  # Change to your email
#     sender_password = "Havealook@123"  # Change to your email password
#     receiver_email = email  # Send OTP to the entered email
#     try:
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(sender_email, sender_password)
#         message = f"Subject: Password Reset OTP\n\nYour OTP for password reset is: {otp}"
#         server.sendmail(sender_email, receiver_email, message)
#         server.quit()
#         print("OTP Email sent successfully!")
#     except Exception as e:
#         print(f"Error sending email: {e}")

# Route: Forgot Password (Enter Email)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        employee_emails = get_employee_emails()  # Load emails from Excel

        print(f"Checking if {email} exists in employee records...")  # Debugging print

        if email in employee_emails:
            otp = generate_otp()
            otp_storage[email] = {'otp': otp, 'expiry': time.time() + 300}  # OTP expires in 5 min
            
            print(f"Generated OTP: {otp}")  # Debugging print

            send_email(email, otp)  # Send the OTP
            
            session['reset_email'] = email
            flash("OTP sent to your email", "success")
            return redirect(url_for('verify_otp'))
        else:
            flash("Email not found in records!", "danger")
            print("Email not found!")  # Debugging print

    return render_template('forgot_password.html')



# @app.route('/forgot_password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         email = request.form['email']
#         employee_emails = get_employee_emails()  # Load emails from Excel

#         if email in employee_emails:
#             otp = generate_otp()
#             otp_storage[email] = {'otp': otp, 'expiry': time.time() + 300}  # OTP expires in 5 minutes
#             send_otp(email, otp)
#             session['reset_email'] = email
#             flash("OTP sent to your email", "success")
#             return redirect(url_for('verify_otp'))
#         else:
#             flash("Email not found in records!", "danger")
#     return render_template('forgot_password.html') 

# Route: Verify OTP

# Route: Verify OTP
# Route: Verify OTP
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        email = session.get('reset_email')

        if not email or email not in otp_storage:
            flash("No OTP found for this email!", "danger")
            return redirect(url_for('forgot_password'))

        stored_otp_info = otp_storage[email]

        print(f"Stored OTP: {stored_otp_info['otp']}")  # Debugging print
        print(f"Entered OTP: {entered_otp}")  # Debugging print

        if stored_otp_info['otp'] == entered_otp and time.time() < stored_otp_info['expiry']:
            flash("OTP Verified! Set a new password.", "success")
            return redirect(url_for('reset_password'))
        else:
            flash("Invalid or Expired OTP!", "danger")
            return redirect(url_for('verify_otp'))  # Redirect back to OTP page

    return render_template('verify_otp.html')  # Ensure a return statement for GET requests




# @app.route('/verify_otp', methods=['GET', 'POST'])
# def verify_otp():
#     if request.method == 'POST':
#         entered_otp = request.form['otp']
#         email = session.get('reset_email')

#         if email in otp_storage :
#            stored_otp_info = otp_storage[email] 
#         if stored_otp_info['otp'] == entered_otp and time.time() < stored_otp_info['expiry']:
#             flash("OTP Verified! Set a new password.", "success")
#             return redirect(url_for('reset_password'))
#         else:
#             flash("Invalid OTP!", "danger")
#     return render_template('verify_otp.html')

 

# Route: Reset Password

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if "reset_email" not in session:
        flash("Session expired! Please request OTP again.", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        email = session.get('reset_email')

        # Update password in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET password = ? WHERE email = ?", (new_password, email))
        conn.commit()
        conn.close()

        flash("Password changed successfully!", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')


# @app.route('/reset_password', methods=['GET', 'POST'])

# def reset_password():

#     if request.method == 'POST':

#         new_password = request.form['new_password']

#         email = session.get('reset_email')

 

#         # Here you need to update the password in the database or Excel (if storing in Excel)

#         flash("Password changed successfully!", "success")

#         return redirect(url_for('login'))

 

#     return render_template('change_password.html')

# Route: Dashboard
@app.route("/dashboard")
def dashboard():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    emp_id = session["emp_id"]
    profile_pic_path = f"profile_pics/{emp_id}.jpg"
    if not os.path.exists(os.path.join("static", profile_pic_path)):
        profile_pic_path = "default_profile.png"

    return render_template("dashboard.html", emp_id=emp_id, profile_pic_filename=profile_pic_path)


# Profile Picture Upload Route
@app.route("/upload_profile_pic", methods=["POST"])
def upload_profile_pic():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    file = request.files.get("profile_pic")
    if file and allowed_file(file.filename):
        filename = f"{session['emp_id']}.jpg"
        save_path = os.path.join("static/profile_pics", filename)
        file.save(save_path)
        flash("Profile picture updated!", "success")
    else:
        flash("Invalid file type! Only images are allowed.", "error")

    return redirect(url_for("dashboard"))

# Route: Download Payslip with Month & Year Selection
@app.route("/download", methods=["POST"])
def download():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    emp_id = session["emp_id"]
    year = request.form["year"]
    month = request.form.get("month", "")  # Month is required only for payslips
    doc_type = request.form["doc_type"]

    # Define directories for each document type
    doc_directories = {
        "payslip": "payslips",
        "bonus": "bonus_slips",
        "form16": "form16"
    }

    if doc_type not in doc_directories:
        flash("Invalid document type!", "error")
        return redirect(url_for("dashboard"))

    doc_folder = os.path.abspath(doc_directories[doc_type])

    # Ensure the folder exists
    if not os.path.exists(doc_folder):
        flash(f"Error: Directory '{doc_folder}' not found!", "error")
        return redirect(url_for("dashboard"))

    # Define filename pattern based on document type
    if doc_type == "payslip":
        month_name = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", 
            "05": "May", "06": "Jun", "07": "Jul", "08": "Aug", 
            "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
        }.get(month, month)

        search_pattern = f"Payslip_{emp_id}_{month_name}_{year}_*.pdf"

    elif doc_type == "bonus":
        search_pattern = f"Bonus_{emp_id}_{year}_*.pdf"

    elif doc_type == "form16":
        search_pattern = f"Form16_{emp_id}_{year}_*.pdf"

    # Debugging: Print available files
    available_files = os.listdir(doc_folder)
    print(f"Available files in {doc_folder}: {available_files}")
    
    # Search for the file
    files = glob.glob(os.path.join(doc_folder, search_pattern))
    print(f"Searching for: {search_pattern}")
    print(f"Files found: {files}")

    if files:
        filename = os.path.basename(files[0])  # Pick the first matching file
        return send_from_directory(doc_folder, filename, as_attachment=True)
    else:
        flash(f"{doc_type.capitalize()} for {year} not found!", "error")
        return redirect(url_for("dashboard"))

# Route: Profile Update

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "emp_id" not in session:
        return redirect(url_for("login"))
    emp_id = session["emp_id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cursor.execute("UPDATE employees SET name = ?, email = ?, phone = ? WHERE emp_id = ?",
                       (name, email, phone, emp_id))
        conn.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    cursor.execute("SELECT name, email, phone FROM employees WHERE emp_id = ?", (emp_id,))
    user = cursor.fetchone()
    conn.close()
    return render_template("profile.html", user=user)

#Route: vehicle

@app.route('/vehicle-reimbursement', methods=['GET'])
def vehicle_reimbursement():
    return render_template('vehicle_reimbursement.html')

@app.route('/submit-vehicle', methods=['POST'])
def submit_vehicle_form():
    data = {
        'tm_name': request.form['tm_name'],
        'mobile': request.form['mobile'],
        'designation': request.form['designation'],
        'email': request.form['email'],
        'grade': request.form['grade'],
        'vehicle': request.form['vehicle'],
        'monthly_balance': request.form['monthly_balance'],
        'declared_value': request.form['declared_value'],
        'bill_name': request.form['bill_name'],
        'amount': request.form['amount'],
        'date': request.form['date']
    }

    # Save as CSV for backup
    with open('vehicle_data.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data.values())

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Vehicle Reimbursement Form", ln=True, align='C')
    pdf.ln(10)
    for key, value in data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf.output("vehicle_data.pdf")

    return redirect(url_for('download_vehicle_pdf'))

@app.route('/download-vehicle-pdf')
def download_vehicle_pdf():
    return send_file("vehicle_data.pdf", as_attachment=True)

# Helper to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home / Form Route
@app.route('/', methods=['GET', 'POST'])
def upload_form():
    if request.method == 'POST':
        file = request.files['attachment']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('view_file', filename=filename))
        else:
            flash("Invalid file type")
    return render_template('your_form.html')

# View Uploaded File

@app.route('/view-submitted')
def view_file():
    # You can customize this to dynamically fetch file name (e.g., from a DB)
    files = os.listdir(UPLOAD_FOLDER)
    if files:
        return send_from_directory(app.config['UPLOAD_FOLDER'], files[-1])  # Show latest uploaded file
    else:
        return "No file uploaded yet", 404
    
#Route:sumbit bill

@app.route('/submit_bill', methods=['POST'])
def submit_bill():
    if 'bill_file' not in request.files:
        return "No file uploaded."

    file = request.files['bill_file']
    if file.filename == '':
        return "No file selected."

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('view_bills'))

#Route: view bills

@app.route('/view_bills')
def view_bills():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    bills = [f for f in files if f.endswith('.pdf')]
    return render_template('view_bills.html', bills=bills)

#Route: Attendance

@app.route('/attendance', methods=['GET'])
def attendance():
    from collections import Counter
    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))

    sample_attendance = {
        1: 'Present', 2: 'Present', 3: 'Absent', 4: 'Leave',
        5: 'Present', 6: 'Absent', 7: 'Present', 10: 'Leave'
    }

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(year, month)

    calendar_data = []
    status_list = []

    for week in month_days:
        week_data = []
        for day in week:
            if day.month == month:
                status = sample_attendance.get(day.day, 'No-data')
                status_list.append(status)
                week_data.append({'date': day, 'status': status})
            else:
                week_data.append(None)
        calendar_data.append(week_data)

    status_count = Counter(status_list)

    return render_template(
        'attendance.html',
        calendar_data=calendar_data,
        month=month,
        year=year,
        current_year=today.year,
        month_name=calendar.month_name[month],
        calendar=calendar,
        status_count=status_count
    )

    
# Route: Change Password

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "emp_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        emp_id = session["emp_id"]
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE emp_id = ? AND password = ?", (emp_id, old_password))
        user = cursor.fetchone()

        if user:
            cursor.execute("UPDATE employees SET password = ? WHERE emp_id = ?", (new_password, emp_id))
            conn.commit()
            conn.close()
            flash("Password changed successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Old password is incorrect!", "error")
    return render_template("change_password.html")

# Route: Logout

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/generate_qr')
def generate_qr():
    link = "https://your-link.com"  # Replace with your actual link
    qr = qrcode.make(link)
    qr.save("qrcode.png")
    return send_file("qrcode.png", mimetype="image/png")

@app.route("/")
def index():
    user_agent = request.headers.get("User-Agent")
    if "Mobile" in user_agent:
        return redirect("https://your-mobile-link.com")
    return "Open on Desktop"

if __name__ == "__main__":
      app.run(host="0.0.0.0", port=5000, debug=True)