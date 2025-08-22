# Overview

The Labour Attendance Management System (LAMS) is a role-based web application for managing employee attendance, assignments, and reporting across multiple companies. The system provides hierarchical access control with four distinct user roles: Master (system administrator), Root (company administrator), Supervisor (team manager), and Employee. Built with Flask and SQLAlchemy, it handles CSV import/export of attendance data, real-time notifications, audit logging, and comprehensive attendance tracking with overtime and deduction management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask**: Chosen for its simplicity and flexibility in building web applications
- **SQLAlchemy**: ORM for database interactions with declarative base models
- **Flask-Login**: Session management and user authentication
- **Werkzeug**: Password hashing and security utilities

## Database Design
- **SQLite for Development**: Easy setup and deployment for proof-of-concept
- **Migration-Ready**: Architecture supports easy transition to PostgreSQL for production
- **Enum-Based Status Management**: Uses Python enums for consistent status tracking (attendance, user roles, notification types)
- **Audit Trail**: Comprehensive logging of all system changes with field-level change tracking

## Authentication & Authorization
- **Role-Based Access Control**: Four-tier permission system (Master > Root > Supervisor > Employee)
- **Company Isolation**: Users can only access data within their assigned company scope
- **Session Management**: Flask-Login handles user sessions and authentication state
- **Password Security**: Werkzeug password hashing with mandatory password change on first login

## Frontend Architecture
- **Server-Side Rendering**: Jinja2 templates with Flask for dynamic content
- **Bootstrap 5**: Dark theme CSS framework for responsive design
- **Vanilla JavaScript**: No frontend frameworks, keeping dependencies minimal
- **Component-Based Templates**: Reusable navbar, sidebar, and modal components

## Data Management
- **CSV Import/Export**: Bulk attendance data processing with validation
- **Real-Time Notifications**: In-app notification system with read/unread tracking
- **Assignment Management**: Date-based employee-to-supervisor assignments
- **Attendance Tracking**: Status management (Present, Absent, Half-Day, Deductions) with overtime support

## Security Features
- **Proxy Fix Middleware**: Handles reverse proxy headers for deployment
- **File Upload Limits**: 16MB maximum file size for CSV uploads
- **Input Validation**: Server-side validation for all form inputs
- **CSRF Protection**: Built into Flask forms and session management

# External Dependencies

## Core Dependencies
- **Flask**: Web framework for Python applications
- **Flask-SQLAlchemy**: Database ORM integration
- **Flask-Login**: User session and authentication management
- **Werkzeug**: WSGI utilities and security helpers
- **Pandas**: CSV data processing and manipulation

## Frontend Dependencies
- **Bootstrap 5**: CSS framework with dark theme from cdn.replit.com
- **Bootstrap Icons**: Icon library for UI elements
- **Vanilla JavaScript**: No external JavaScript frameworks

## Database
- **SQLite**: Default database for development (file-based storage)
- **PostgreSQL Ready**: Schema designed for easy migration to production database

## File Processing
- **CSV Processing**: Built-in Python csv module and Pandas for data import/export
- **Secure Filename**: Werkzeug utilities for safe file handling

## Deployment
- **WSGI Compatible**: Standard Python web server interface
- **Environment Variables**: Configuration through DATABASE_URL and SESSION_SECRET
- **Proxy Support**: Built-in support for reverse proxy deployments

## Logging
- **Python Logging**: Built-in logging module for debugging and audit trails
- **Debug Mode**: Development-friendly error handling and auto-reload