from datetime import datetime, date
from enum import Enum
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, CheckConstraint
from app import db
import json

class UserRole(Enum):
    MASTER = 'MASTER'
    ROOT = 'ROOT'
    SUPERVISOR = 'SUPERVISOR'
    EMPLOYEE = 'EMPLOYEE'

class AttendanceStatus(Enum):
    PRESENT = 'P'
    ABSENT = 'A'
    HALF_DAY = '-0.5'
    FULL_DAY_DEDUCTION = '-1'

class NotificationType(Enum):
    LATENESS = 'LATENESS'
    ABSENCE = 'ABSENCE'
    OVERTIME = 'OVERTIME'
    ASSIGNMENT_CHANGE = 'ASSIGNMENT_CHANGE'
    REMARK = 'REMARK'
    ANNOUNCEMENT = 'ANNOUNCEMENT'

class AuditAction(Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    RESTORE = 'RESTORE'
    IMPORT = 'IMPORT'

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='company_ref', lazy='dynamic')
    employees = db.relationship('Employee', backref='company_ref', lazy='dynamic')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    ep_number = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='user_ref', uselist=False)
    supervisor_profile = db.relationship('SupervisorProfile', backref='user_ref', uselist=False)
    notifications = db.relationship('Notification', backref='recipient_ref', lazy='dynamic')
    remarks = db.relationship('Remark', backref='author_ref', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='actor_ref', lazy='dynamic')

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    ep_number = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    plant = db.Column(db.String(50))
    department = db.Column(db.String(50))
    trade = db.Column(db.String(50))
    skill = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: ep_number per company
    __table_args__ = (
        UniqueConstraint('company_id', 'ep_number', name='uq_company_ep_number'),
    )
    
    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='employee_ref', lazy='dynamic')
    assignments = db.relationship('Assignment', backref='employee_ref', lazy='dynamic')

class SupervisorProfile(db.Model):
    __tablename__ = 'supervisor_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('Assignment', backref='supervisor_ref', lazy='dynamic')

class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisor_profiles.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Null means open-ended
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('User', backref='created_assignments')

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)  # Denormalized
    date = db.Column(db.Date, nullable=False)
    
    # Attendance times
    in1 = db.Column(db.Time, nullable=True)
    out1 = db.Column(db.Time, nullable=True)
    in2 = db.Column(db.Time, nullable=True)
    out2 = db.Column(db.Time, nullable=True)
    in3 = db.Column(db.Time, nullable=True)
    out3 = db.Column(db.Time, nullable=True)
    
    # Hours and status
    hours_worked = db.Column(db.Numeric(5, 2), default=0.0)
    overtime = db.Column(db.Numeric(5, 2), default=0.0)
    status = db.Column(db.Enum(AttendanceStatus), nullable=False)
    
    # Metadata
    plant = db.Column(db.String(50))
    department = db.Column(db.String(50))
    trade = db.Column(db.String(50))
    skill = db.Column(db.String(50))
    
    # Edit tracking
    last_edit_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    last_edit_at = db.Column(db.DateTime, nullable=True)
    remarks_count = db.Column(db.Integer, default=0)
    soft_deleted = db.Column(db.Boolean, default=False)
    
    # Unique constraint: employee + date
    __table_args__ = (
        UniqueConstraint('employee_id', 'date', name='uq_employee_date'),
    )
    
    # Relationships
    last_edit_by = db.relationship('User', backref='edited_records')
    remarks = db.relationship('Remark', backref='attendance_ref', lazy='dynamic')

class Remark(db.Model):
    __tablename__ = 'remarks'
    
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance_records.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(NotificationType), nullable=False)
    related_object_type = db.Column(db.String(50), nullable=True)
    related_object_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.Enum(AuditAction), nullable=False)
    object_type = db.Column(db.String(50), nullable=False)
    object_id = db.Column(db.Integer, nullable=False)
    field_changes = db.Column(db.Text, nullable=True)  # JSON string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    context = db.Column(db.String(200), nullable=True)
    
    def get_field_changes(self):
        """Parse field changes JSON"""
        if self.field_changes:
            try:
                return json.loads(self.field_changes)
            except:
                return {}
        return {}
    
    def set_field_changes(self, changes_dict):
        """Set field changes as JSON"""
        if changes_dict:
            self.field_changes = json.dumps(changes_dict)

class DashboardPreference(db.Model):
    __tablename__ = 'dashboard_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    layout = db.Column(db.Text, nullable=True)  # JSON string
    
    # Relationships
    user = db.relationship('User', backref='dashboard_preference')
