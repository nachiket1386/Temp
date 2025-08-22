from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from models import *
from app import db
import pandas as pd
from datetime import datetime, time
import logging
import io
import tempfile
from werkzeug.security import generate_password_hash

def requires_role(*allowed_roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.role not in allowed_roles:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_companies():
    """Get companies visible to current user"""
    if current_user.role == UserRole.MASTER:
        return Company.query.all()
    elif current_user.company_id:
        return [Company.query.get(current_user.company_id)]
    return []

def create_audit_log(actor_id, action, object_type, object_id, field_changes=None, context=None):
    """Create an audit log entry"""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        context=context
    )
    
    if field_changes:
        log.set_field_changes(field_changes)
    
    db.session.add(log)
    return log

def parse_time(time_str):
    """Parse time string in HH:MM format"""
    if not time_str or time_str.strip() == '':
        return None
    
    try:
        return datetime.strptime(time_str.strip(), '%H:%M').time()
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")

def parse_date(date_str):
    """Parse date string in DD-MM-YYYY format"""
    if not date_str:
        raise ValueError("Date is required")
    
    try:
        return datetime.strptime(date_str.strip(), '%d-%m-%Y').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected DD-MM-YYYY")

def validate_status(status_str):
    """Validate attendance status"""
    valid_statuses = [s.value for s in AttendanceStatus]
    if status_str not in valid_statuses:
        raise ValueError(f"Invalid status: {status_str}. Must be one of {valid_statuses}")
    return status_str

def process_csv_import(file, user_id, commit=False):
    """Process CSV attendance import"""
    try:
        # Read CSV
        df = pd.read_csv(file)
        
        # Expected columns
        expected_columns = [
            'EP number', 'Name', 'Company', 'Plant', 'Department', 'Trade', 'Skill',
            'Date', 'IN1', 'OUT1', 'IN2', 'OUT2', 'IN3', 'OUT3', 
            'Hours Worked', 'Overtime', 'Status'
        ]
        
        # Check columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            return {
                'success': False,
                'error': f"Missing required columns: {', '.join(missing_columns)}"
            }
        
        results = {
            'success': True,
            'summary': {
                'total_rows': len(df),
                'valid_rows': 0,
                'error_rows': 0,
                'created': 0,
                'updated': 0
            },
            'errors': []
        }
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                ep_number = str(row['EP number']).strip()
                name = str(row['Name']).strip()
                company_name = str(row['Company']).strip()
                date_str = str(row['Date']).strip()
                status = str(row['Status']).strip()
                
                if not ep_number or ep_number == 'nan':
                    raise ValueError("EP number is required")
                
                if not company_name or company_name == 'nan':
                    raise ValueError("Company is required")
                
                # Validate and parse data
                attendance_date = parse_date(date_str)
                validate_status(status)
                
                # Parse times
                in1 = parse_time(str(row['IN1']) if not pd.isna(row['IN1']) else '')
                out1 = parse_time(str(row['OUT1']) if not pd.isna(row['OUT1']) else '')
                in2 = parse_time(str(row['IN2']) if not pd.isna(row['IN2']) else '')
                out2 = parse_time(str(row['OUT2']) if not pd.isna(row['OUT2']) else '')
                in3 = parse_time(str(row['IN3']) if not pd.isna(row['IN3']) else '')
                out3 = parse_time(str(row['OUT3']) if not pd.isna(row['OUT3']) else '')
                
                # Parse hours
                try:
                    hours_worked = float(row['Hours Worked']) if not pd.isna(row['Hours Worked']) else 0.0
                    overtime = float(row['Overtime']) if not pd.isna(row['Overtime']) else 0.0
                except ValueError:
                    raise ValueError("Hours Worked and Overtime must be numeric")
                
                # Find or create company
                company = Company.query.filter_by(name=company_name).first()
                if not company:
                    raise ValueError(f"Unknown company: {company_name}")
                
                if commit:
                    # Find or create employee
                    employee = Employee.query.filter_by(
                        company_id=company.id,
                        ep_number=ep_number
                    ).first()
                    
                    if not employee:
                        # Create employee
                        employee = Employee(
                            company_id=company.id,
                            ep_number=ep_number,
                            name=name,
                            plant=str(row['Plant']) if not pd.isna(row['Plant']) else '',
                            department=str(row['Department']) if not pd.isna(row['Department']) else '',
                            trade=str(row['Trade']) if not pd.isna(row['Trade']) else '',
                            skill=str(row['Skill']) if not pd.isna(row['Skill']) else ''
                        )
                        db.session.add(employee)
                        db.session.flush()
                        
                        # Create employee user account
                        if not User.query.filter_by(username=ep_number).first():
                            user = User(
                                username=ep_number,
                                ep_number=ep_number,
                                role=UserRole.EMPLOYEE,
                                company_id=company.id,
                                password_hash=generate_password_hash(ep_number),
                                must_change_password=True
                            )
                            db.session.add(user)
                            db.session.flush()
                            employee.user_id = user.id
                    
                    # Find or create attendance record
                    attendance = AttendanceRecord.query.filter_by(
                        employee_id=employee.id,
                        date=attendance_date
                    ).first()
                    
                    is_new = not attendance
                    
                    if not attendance:
                        attendance = AttendanceRecord(
                            employee_id=employee.id,
                            company_id=company.id,
                            date=attendance_date,
                            status=AttendanceStatus(status)
                        )
                        db.session.add(attendance)
                        results['summary']['created'] += 1
                    else:
                        results['summary']['updated'] += 1
                    
                    # Update fields (only non-empty values overwrite existing)
                    if in1 is not None or is_new:
                        attendance.in1 = in1
                    if out1 is not None or is_new:
                        attendance.out1 = out1
                    if in2 is not None or is_new:
                        attendance.in2 = in2
                    if out2 is not None or is_new:
                        attendance.out2 = out2
                    if in3 is not None or is_new:
                        attendance.in3 = in3
                    if out3 is not None or is_new:
                        attendance.out3 = out3
                    
                    attendance.hours_worked = hours_worked
                    attendance.overtime = overtime
                    attendance.status = AttendanceStatus(status)
                    attendance.plant = str(row['Plant']) if not pd.isna(row['Plant']) else ''
                    attendance.department = str(row['Department']) if not pd.isna(row['Department']) else ''
                    attendance.trade = str(row['Trade']) if not pd.isna(row['Trade']) else ''
                    attendance.skill = str(row['Skill']) if not pd.isna(row['Skill']) else ''
                
                results['summary']['valid_rows'] += 1
                
            except Exception as e:
                results['summary']['error_rows'] += 1
                results['errors'].append(f"Row {index + 2}: {str(e)}")
        
        if commit:
            db.session.commit()
        
        return results
        
    except Exception as e:
        logging.error(f"CSV import error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def export_attendance_csv(user):
    """Export attendance data based on user permissions"""
    query = AttendanceRecord.query
    
    # Apply role-based filtering
    if user.role == UserRole.MASTER:
        # Master can export all data
        pass
    elif user.role == UserRole.ROOT:
        # Root can export company data
        query = query.filter_by(company_id=user.company_id)
    elif user.role == UserRole.SUPERVISOR:
        # Supervisor can export assigned employees
        if user.supervisor_profile:
            assigned_employee_ids = db.session.query(Assignment.employee_id).filter_by(
                supervisor_id=user.supervisor_profile.id
            ).filter(
                db.or_(Assignment.end_date.is_(None), Assignment.end_date >= date.today())
            ).subquery()
            
            query = query.filter(AttendanceRecord.employee_id.in_(assigned_employee_ids))
    elif user.role == UserRole.EMPLOYEE:
        # Employee can export own data
        if user.employee:
            query = query.filter_by(employee_id=user.employee.id)
    
    # Execute query and build CSV
    records = query.join(Employee).all()
    
    data = []
    for record in records:
        employee = record.employee_ref
        data.append({
            'EP number': employee.ep_number,
            'Name': employee.name,
            'Company': employee.company_ref.name,
            'Plant': record.plant or '',
            'Department': record.department or '',
            'Trade': record.trade or '',
            'Skill': record.skill or '',
            'Date': record.date.strftime('%d-%m-%Y'),
            'IN1': record.in1.strftime('%H:%M') if record.in1 else '',
            'OUT1': record.out1.strftime('%H:%M') if record.out1 else '',
            'IN2': record.in2.strftime('%H:%M') if record.in2 else '',
            'OUT2': record.out2.strftime('%H:%M') if record.out2 else '',
            'IN3': record.in3.strftime('%H:%M') if record.in3 else '',
            'OUT3': record.out3.strftime('%H:%M') if record.out3 else '',
            'Hours Worked': str(record.hours_worked),
            'Overtime': str(record.overtime),
            'Status': record.status.value
        })
    
    df = pd.DataFrame(data)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    df.to_csv(temp_file.name, index=False)
    
    return temp_file.name

def get_unread_notifications_count(user_id: int) -> int:
    """Get count of unread notifications for a user"""
    return Notification.query.filter_by(recipient_id=user_id).filter(Notification.read_at.is_(None)).count()
