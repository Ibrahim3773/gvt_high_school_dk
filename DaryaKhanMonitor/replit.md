# Attendance Monitoring System - Govt. High School Darya Khan

## Overview

This is a Flask-based web application designed for managing student attendance at Govt. High School Darya Khan. The system enables school administrators to:

- Upload and manage student records from CSV/Excel files
- Mark daily attendance for students with class and section filtering
- View attendance records with comprehensive filtering options
- Send SMS notifications to parents of absent students via Twilio integration

The application provides a straightforward interface for attendance tracking and automated parent communication, helping schools maintain better oversight of student attendance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Framework
**Problem:** Need for a lightweight, easy-to-deploy web application for attendance management  
**Solution:** Flask web framework with server-side rendering using Jinja2 templates  
**Rationale:** Flask provides simplicity and flexibility for small to medium-scale applications without unnecessary complexity. Server-side rendering reduces client-side complexity and works well for form-heavy applications.

### Data Storage
**Problem:** Reliable storage for student and attendance records  
**Solution:** SQLite relational database with two main tables:
- `students` table: Stores student information (name, roll number, class, section, parent details)
- `attendance` table: Records daily attendance with foreign key relationship to students

**Rationale:** SQLite offers zero-configuration deployment, ACID compliance, and sufficient performance for single-school use cases. The relational model ensures data integrity through foreign keys and unique constraints.

**Key Design Decisions:**
- Composite unique constraint on (student_id, date) in attendance table prevents duplicate entries
- Roll numbers enforced as unique identifiers for students
- Row factory configuration enables dictionary-like access to query results

### File Upload System
**Problem:** Bulk import of student data from external sources  
**Solution:** File upload handler supporting CSV and Excel formats (csv, xlsx, xls) using pandas for parsing  
**Configuration:**
- Maximum file size: 16MB
- Secure filename sanitization using werkzeug utilities
- Dedicated uploads directory for file storage

**Rationale:** Pandas provides robust data parsing for multiple formats. File size limits and sanitization prevent security vulnerabilities and server resource exhaustion.

### Frontend Architecture
**Problem:** User-friendly interface accessible on various devices  
**Solution:** Bootstrap 5 responsive framework with Bootstrap Icons  
**Design Pattern:** Template inheritance using Jinja2 base template
- Consistent navigation across all pages
- Responsive layout adapting to mobile and desktop
- Icon-based visual indicators for better UX

**Rationale:** Bootstrap accelerates development with pre-built responsive components. Template inheritance ensures consistency and maintainability.

### Attendance Management
**Problem:** Efficient daily attendance marking for multiple students  
**Solution:** Filter-based interface allowing selection by:
- Date
- Class
- Section

**Design Pattern:** Query parameter-based filtering with GET requests for stateful URLs that can be bookmarked or shared

**Rationale:** Server-side filtering reduces data transfer and enables precise record retrieval. GET-based filters allow direct URL access to specific views.

### Session Management
**Problem:** Secure flash messaging for user feedback  
**Solution:** Flask's built-in session management with configurable secret key
- Environment variable support for production: `SESSION_SECRET`
- Fallback development key for local testing

**Rationale:** Environment-based configuration enables secure production deployment while maintaining development convenience.

## External Dependencies

### SMS Communication Service
**Integration:** Twilio REST API client  
**Purpose:** Automated SMS notifications to parents of absent students  
**Implementation:** Python Twilio SDK for API communication  
**Configuration Requirements:**
- Twilio account credentials (Account SID, Auth Token)
- Verified phone number for sending messages
- Parent contact numbers stored in student records

### Data Processing Library
**Integration:** Pandas library  
**Purpose:** Parse and process CSV/Excel file uploads  
**Supported Formats:**
- CSV (Comma-Separated Values)
- XLSX (Excel 2007+)
- XLS (Excel 97-2003)

**Required Columns:**
- name (student full name)
- roll_number (unique identifier)
- class (grade level)
- section (class division)
- parent_name (guardian name)
- parent_contact (phone number for SMS)

### UI Framework
**Integration:** Bootstrap 5 CDN  
**Components Used:**
- Responsive grid system
- Form controls and validation
- Navigation components
- Card layouts

**Integration:** Bootstrap Icons CDN  
**Purpose:** Consistent iconography throughout the interface

### Python Web Framework
**Framework:** Flask  
**Key Extensions/Features Used:**
- Template rendering (Jinja2)
- Request handling and routing
- File upload utilities (werkzeug)
- Flash messaging
- JSON responses for potential API endpoints

### Database
**Engine:** SQLite3 (Python standard library)  
**Connection Pattern:** Function-based connection factory with Row factory for dict-like access  
**Schema Management:** Manual SQL execution for table creation (init_db function)

**Note:** While the current implementation uses SQLite, the architecture could be migrated to PostgreSQL with minimal changes to support multi-user concurrent access or larger deployments.