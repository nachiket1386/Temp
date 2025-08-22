from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, UserRole
from app import db
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password.', 'error')
            return render_template('login.html')
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact your administrator.', 'error')
            return render_template('login.html')
        
        login_user(user)
        logging.info(f"User {username} logged in with role {user.role.value}")
        
        # Check if password change is required
        if user.must_change_password:
            return redirect(url_for('auth.change_password'))
        
        # Redirect to appropriate dashboard
        return redirect(url_for('views.dashboard'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('login.html', change_password=True)
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
            return render_template('login.html', change_password=True)
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('login.html', change_password=True)
        
        current_user.password_hash = generate_password_hash(new_password)
        current_user.must_change_password = False
        db.session.commit()
        
        flash('Password changed successfully.', 'success')
        return redirect(url_for('views.dashboard'))
    
    return render_template('login.html', change_password=True)

@auth_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    # Only Master can reset User1, User1 can reset User2/User3
    target_user = User.query.get_or_404(user_id)
    
    can_reset = False
    if current_user.role == UserRole.MASTER and target_user.role == UserRole.ROOT:
        can_reset = True
    elif current_user.role == UserRole.ROOT and target_user.role in [UserRole.SUPERVISOR, UserRole.EMPLOYEE]:
        can_reset = True
    
    if not can_reset:
        flash('You do not have permission to reset this user\'s password.', 'error')
        return redirect(request.referrer or url_for('views.dashboard'))
    
    # Reset password to EP number or username
    new_password = target_user.ep_number if target_user.ep_number else target_user.username
    target_user.password_hash = generate_password_hash(new_password)
    target_user.must_change_password = True
    db.session.commit()
    
    flash(f'Password reset for {target_user.username}. New password: {new_password}', 'success')
    return redirect(request.referrer or url_for('views.dashboard'))
