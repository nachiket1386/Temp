from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from models import *
from app import db
from utils import requires_role, get_user_companies, create_audit_log, process_csv_import, export_attendance_csv, get_unread_notifications_count
import logging
import pandas as pd
from datetime import datetime, date
import io
import os

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
@login_required
def dashboard():
    """Role-based dashboard"""
    context = {
        'user': current_user,
        'notifications': get_unread_notifications_count(current_user.id)
    }
    
    if current_user.role == UserRole.MASTER:
        context.update({
            'companies_count': Company.query.count(),
            'users_count': User.query.count(),
            'recent_imports': AuditLog.query.filter_by(action=AuditAction.IMPORT).limit(5).all()
        })
    
    elif current_user.role == UserRole.ROOT:
        if current_user.company_id:
            company = Company.query.get(current_user.company_id)
            context.update({
                'company': company,
                'employees_count': Employee.query.filter_by(company_id=current_user.company_id).count(),
                'supervisors_count': User.query.filter_by(company_id=current_user.company_id, role=UserRole.SUPERVISOR).count()
            })
    
    elif current_user.role == UserRole.SUPERVISOR:
        if current_user.supervisor_profile:
            assigned_employees = db.session.query(Employee).join(Assignment).filter(
                Assignment.supervisor_id == current_user.supervisor_profile.id,
                db.or_(Assignment.end_date.is_(None), Assignment.end_date >= date.today())
            ).count()
            
            context.update({
                'assigned_employees': assigned_employees,
                'today_attendance': AttendanceRecord.query.filter_by(date=date.today()).count()
            })
    
    elif current_user.role == UserRole.EMPLOYEE:
        if current_user.employee:
            context.update({
                'employee': current_user.employee,
                'this_month_records': current_user.employee.attendance_records.filter(
                    AttendanceRecord.date >= date.today().replace(day=1)
                ).count()
            })
    
    return render_template('dashboard.html', **context)

# Master Views
@views_bp.route('/companies')
@requires_role(UserRole.MASTER)
def companies():
    companies = Company.query.all()
    from utils import get_unread_notifications_count
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('master/companies.html', companies=companies, notifications=notifications)

@views_bp.route('/companies/create', methods=['POST'])
@requires_role(UserRole.MASTER)
def create_company():
    name = request.form.get('name', '').strip()
    
    if not name:
        flash('Company name is required.', 'error')
        return redirect(url_for('views.companies'))
    
    if Company.query.filter_by(name=name).first():
        flash('Company with this name already exists.', 'error')
        return redirect(url_for('views.companies'))
    
    company = Company(name=name)
    db.session.add(company)
    db.session.commit()
    
    create_audit_log(current_user.id, AuditAction.CREATE, 'Company', company.id, {'name': name})
    flash(f'Company "{name}" created successfully.', 'success')
    return redirect(url_for('views.companies'))

@views_bp.route('/users')
@requires_role(UserRole.MASTER)
def master_users():
    users = User.query.filter(User.role != UserRole.MASTER).all()
    companies = Company.query.all()
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('master/users.html', users=users, companies=companies, notifications=notifications)

@views_bp.route('/users/create-root', methods=['POST'])
@requires_role(UserRole.MASTER)
def create_root_user():
    username = request.form.get('username', '').strip()
    company_id = request.form.get('company_id')
    
    if not username or not company_id:
        flash('Username and company are required.', 'error')
        return redirect(url_for('views.master_users'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('views.master_users'))
    
    company = Company.query.get(company_id)
    if not company:
        flash('Invalid company selected.', 'error')
        return redirect(url_for('views.master_users'))
    
    user = User(
        username=username,
        role=UserRole.ROOT,
        company_id=company_id,
        password_hash=generate_password_hash(username),  # Initial password = username
        must_change_password=True
    )
    db.session.add(user)
    db.session.commit()
    
    create_audit_log(current_user.id, AuditAction.CREATE, 'User', user.id, 
                    {'username': username, 'role': 'ROOT', 'company': company.name})
    flash(f'Root user "{username}" created successfully. Initial password: {username}', 'success')
    return redirect(url_for('views.master_users'))

@views_bp.route('/import-attendance')
@requires_role(UserRole.MASTER)
def import_attendance():
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('master/import.html', notifications=notifications)

@views_bp.route('/download-template')
@requires_role(UserRole.MASTER)
def download_template():
    """Download CSV template"""
    template_data = {
        'EP number': ['EP001', 'EP002'],
        'Name': ['John Doe', 'Jane Smith'],
        'Company': ['Company A', 'Company A'],
        'Plant': ['Plant1', 'Plant1'],
        'Department': ['Assembly', 'Assembly'],
        'Trade': ['Welder', 'Fitter'],
        'Skill': ['Skilled', 'Semi'],
        'Date': ['22-08-2025', '22-08-2025'],
        'IN1': ['09:00', '09:00'],
        'OUT1': ['13:00', '13:00'],
        'IN2': ['14:00', '14:00'],
        'OUT2': ['18:00', '18:00'],
        'IN3': ['', ''],
        'OUT3': ['', ''],
        'Hours Worked': ['8.00', '8.00'],
        'Overtime': ['1.00', '0.00'],
        'Status': ['P', 'P']
    }
    
    df = pd.DataFrame(template_data)
    
    # Create in-memory file
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.read()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='attendance_template.csv'
    )

@views_bp.route('/upload-csv', methods=['POST'])
@requires_role(UserRole.MASTER)
def upload_csv():
    if 'file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('views.import_attendance'))
    
    file = request.files['file']
    if not file.filename or not file.filename.endswith('.csv'):
        flash('Please select a valid CSV file.', 'error')
        return redirect(url_for('views.import_attendance'))
    
    mode = request.form.get('mode', 'validate')  # validate or commit
    
    try:
        result = process_csv_import(file, current_user.id, mode == 'commit')
        
        if result['success']:
            if mode == 'validate':
                flash(f'Validation complete. {result["summary"]["valid_rows"]} valid rows, {result["summary"]["error_rows"]} errors.', 'info')
            else:
                flash(f'Import successful! Created: {result["summary"]["created"]}, Updated: {result["summary"]["updated"]}, Errors: {result["summary"]["error_rows"]}', 'success')
                create_audit_log(current_user.id, AuditAction.IMPORT, 'AttendanceRecord', 0, 
                               {'filename': secure_filename(file.filename or 'unknown.csv'), 'summary': result['summary']})
        else:
            flash(f'Import failed: {result["error"]}', 'error')
            
    except Exception as e:
        logging.error(f"CSV import error: {str(e)}")
        flash(f'Import failed: {str(e)}', 'error')
    
    return redirect(url_for('views.import_attendance'))

@views_bp.route('/audit')
@requires_role(UserRole.MASTER)
def audit():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('master/audit.html', logs=logs, notifications=notifications)

# Root User Views
@views_bp.route('/supervisors')
@requires_role(UserRole.ROOT)
def supervisors():
    supervisors = User.query.filter_by(
        company_id=current_user.company_id, 
        role=UserRole.SUPERVISOR
    ).all()
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('root/supervisors.html', supervisors=supervisors, notifications=notifications)

@views_bp.route('/supervisors/create', methods=['POST'])
@requires_role(UserRole.ROOT)
def create_supervisor():
    ep_number = request.form.get('ep_number', '').strip()
    
    if not ep_number:
        flash('EP number is required.', 'error')
        return redirect(url_for('views.supervisors'))
    
    # Check if EP exists as employee
    employee = Employee.query.filter_by(
        company_id=current_user.company_id, 
        ep_number=ep_number
    ).first()
    
    if not employee:
        flash('Employee with this EP number does not exist.', 'error')
        return redirect(url_for('views.supervisors'))
    
    if User.query.filter_by(username=ep_number).first():
        flash('User with this EP number already exists.', 'error')
        return redirect(url_for('views.supervisors'))
    
    # Create supervisor user
    user = User(
        username=ep_number,
        ep_number=ep_number,
        role=UserRole.SUPERVISOR,
        company_id=current_user.company_id,
        password_hash=generate_password_hash(ep_number),
        must_change_password=True
    )
    db.session.add(user)
    db.session.flush()
    
    # Create supervisor profile
    profile = SupervisorProfile(
        user_id=user.id,
        company_id=current_user.company_id
    )
    db.session.add(profile)
    db.session.commit()
    
    create_audit_log(current_user.id, AuditAction.CREATE, 'User', user.id, 
                    {'username': ep_number, 'role': 'SUPERVISOR'})
    flash(f'Supervisor "{ep_number}" created successfully. Initial password: {ep_number}', 'success')
    return redirect(url_for('views.supervisors'))

@views_bp.route('/assignments')
@requires_role(UserRole.ROOT)
def assignments():
    employees = Employee.query.filter_by(company_id=current_user.company_id).all()
    supervisors = db.session.query(User, SupervisorProfile).join(SupervisorProfile).filter(
        User.company_id == current_user.company_id
    ).all()
    
    # Get current assignments  
    current_assignments = db.session.query(Assignment, Employee, User).select_from(Assignment).join(
        Employee, Assignment.employee_id == Employee.id
    ).join(
        SupervisorProfile, Assignment.supervisor_id == SupervisorProfile.id
    ).join(User, SupervisorProfile.user_id == User.id).filter(
        Employee.company_id == current_user.company_id,
        db.or_(Assignment.end_date.is_(None), Assignment.end_date >= date.today())
    ).all()
    
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('root/assignments.html', 
                         employees=employees, 
                         supervisors=supervisors,
                         current_assignments=current_assignments,
                         notifications=notifications)

@views_bp.route('/assignments/create', methods=['POST'])
@requires_role(UserRole.ROOT)
def create_assignment():
    employee_id = request.form.get('employee_id')
    supervisor_id = request.form.get('supervisor_id')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date', '')
    
    if not all([employee_id, supervisor_id, start_date_str]):
        flash('Employee, supervisor, and start date are required.', 'error')
        return redirect(url_for('views.assignments'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        if end_date and end_date < start_date:
            flash('End date cannot be before start date.', 'error')
            return redirect(url_for('views.assignments'))
        
        # Check for overlapping assignments
        query = Assignment.query.filter_by(employee_id=employee_id).filter(
            db.or_(Assignment.end_date.is_(None), Assignment.end_date >= start_date)
        )
        
        if end_date:
            query = query.filter(Assignment.start_date <= end_date)
        
        if query.first():
            flash('This employee already has an overlapping assignment.', 'error')
            return redirect(url_for('views.assignments'))
        
        assignment = Assignment(
            employee_id=employee_id,
            supervisor_id=supervisor_id,
            start_date=start_date,
            end_date=end_date,
            created_by_id=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        
        create_audit_log(current_user.id, AuditAction.CREATE, 'Assignment', assignment.id,
                        {'employee_id': employee_id, 'supervisor_id': supervisor_id})
        flash('Assignment created successfully.', 'success')
        
    except ValueError:
        flash('Invalid date format.', 'error')
    except Exception as e:
        logging.error(f"Assignment creation error: {str(e)}")
        flash('Failed to create assignment.', 'error')
    
    return redirect(url_for('views.assignments'))

# Supervisor Views
@views_bp.route('/attendance')
@requires_role(UserRole.SUPERVISOR)
def supervisor_attendance():
    if not current_user.supervisor_profile:
        flash('Supervisor profile not found.', 'error')
        return redirect(url_for('views.dashboard'))
    
    # Get assigned employees
    assigned_query = db.session.query(Employee, AttendanceRecord).outerjoin(
        AttendanceRecord
    ).join(Assignment).filter(
        Assignment.supervisor_id == current_user.supervisor_profile.id,
        db.or_(Assignment.end_date.is_(None), Assignment.end_date >= date.today())
    )
    
    # Apply filters
    status_filter = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if status_filter:
        assigned_query = assigned_query.filter(AttendanceRecord.status == status_filter)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            assigned_query = assigned_query.filter(AttendanceRecord.date >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            assigned_query = assigned_query.filter(AttendanceRecord.date <= date_to_obj)
        except ValueError:
            pass
    
    page = request.args.get('page', 1, type=int)
    records = assigned_query.paginate(page=page, per_page=20, error_out=False)
    
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('supervisor/attendance.html', 
                         records=records,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to,
                         notifications=notifications)

# Employee Views
@views_bp.route('/my-records')
@requires_role(UserRole.EMPLOYEE)
def employee_records():
    if not current_user.employee:
        flash('Employee profile not found.', 'error')
        return redirect(url_for('views.dashboard'))
    
    # Monthly summary
    current_month_start = date.today().replace(day=1)
    monthly_records = current_user.employee.attendance_records.filter(
        AttendanceRecord.date >= current_month_start
    ).all()
    
    status_summary = {}
    for status in AttendanceStatus:
        status_summary[status.value] = sum(1 for r in monthly_records if r.status == status)
    
    # Get filtered records
    status_filter = request.args.get('status')
    query = current_user.employee.attendance_records
    
    if status_filter:
        query = query.filter(AttendanceRecord.status == status_filter)
    
    page = request.args.get('page', 1, type=int)
    records = query.order_by(AttendanceRecord.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    notifications = get_unread_notifications_count(current_user.id)
    return render_template('employee/records.html',
                         records=records,
                         status_summary=status_summary,
                         status_filter=status_filter,
                         notifications=notifications)

# Common Views
@views_bp.route('/export')
@login_required
def export_data():
    """Export attendance data based on user role and permissions"""
    try:
        filename = export_attendance_csv(current_user)
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Export error: {str(e)}")
        flash('Failed to export data.', 'error')
        return redirect(request.referrer or url_for('views.dashboard'))

@views_bp.route('/add-remark/<int:attendance_id>', methods=['POST'])
@login_required
def add_remark(attendance_id):
    record = AttendanceRecord.query.get_or_404(attendance_id)
    text = request.form.get('remark', '').strip()
    
    if not text:
        flash('Remark text is required.', 'error')
        return redirect(request.referrer)
    
    # Check permissions
    can_add = False
    if current_user.role == UserRole.EMPLOYEE and record.employee.user_id == current_user.id:
        can_add = True
    elif current_user.role == UserRole.SUPERVISOR:
        # Check if this employee is assigned to current supervisor
        assignment = Assignment.query.filter_by(
            employee_id=record.employee_id,
            supervisor_id=current_user.supervisor_profile.id
        ).filter(
            Assignment.start_date <= record.date,
            db.or_(Assignment.end_date.is_(None), Assignment.end_date >= record.date)
        ).first()
        if assignment:
            can_add = True
    
    if not can_add:
        flash('You do not have permission to add remarks to this record.', 'error')
        return redirect(request.referrer)
    
    remark = Remark(
        attendance_id=attendance_id,
        author_id=current_user.id,
        text=text
    )
    db.session.add(remark)
    
    # Update remarks count
    record.remarks_count = record.remarks.count() + 1
    db.session.commit()
    
    flash('Remark added successfully.', 'success')
    return redirect(request.referrer)

@views_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = current_user.notifications.order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    notifications_count = get_unread_notifications_count(current_user.id)
    return render_template('notifications.html', notifications=notifications_count, notifications_list=notifications)

@views_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id, 
        recipient_id=current_user.id
    ).first_or_404()
    
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return redirect(request.referrer or url_for('views.notifications'))
