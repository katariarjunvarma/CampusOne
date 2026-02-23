# CampusOne – Campus Management System

## 🔗 Project Links

| Resource | Link |
|----------|------|
| **GitHub Repository** | [github.com/arjunvarma/CampusOne](https://github.com/katariarjunvarma/CampusOne) |
| **Live Demo** | [campusone-smartlpu.onrender.com](https://campusone-u5ro.onrender.com/accounts/login/) |

---

## 📹 Video Demonstrations

| Module | Description | Watch |
|--------|-------------|-------|
| **1. Smart Attendance Management System** | Face recognition & attendance tracking | [Google Drive](https://drive.google.com/file/d/1ruRNOUdZbyejFUpOfZoD715rrBy63HXx/view?usp=sharing) |
| **2. Smart Food Stall Pre-Ordering System** | Order management & vendor dashboard | [Google Drive](https://drive.google.com/file/d/1bBfH2QdjS7snAhwZIsopdWzicfudlB9m/view?usp=sharing) |
| **3. Campus Resource & Parameter Estimation** | Resource optimization & analytics | [Google Drive](https://drive.google.com/file/d/1t5pv_0VPhlMSDRbqt63cr9XmyLJxEtM-/view?usp=sharing) |
| **4. Make-Up Class & Remedial Module** | Scheduling & remedial management | [Google Drive](https://drive.google.com/file/d/1KykmE1TEyM-om1LOx_3ub1pIdhZqt7PI/view?usp=sharing) |

---

## 📖 Documentation

**Blog Post:** [Building CampusOne: An AI-Powered Campus Management System with Django and OpenCV](https://medium.com/@arjunvarma5110/building-campusone-an-ai-powered-campus-management-system-with-django-and-opencv-3f52ead5851e)

---

CampusOne is a comprehensive **AI-powered Campus Management System** built with Django and OpenCV, designed to streamline academic and operational workflows. The platform integrates multiple modules including Smart Attendance with face recognition, Food Pre-Ordering, Campus Resource Analytics, and Make-Up Class Management.

## 🎯 System Overview

CampusOne provides role-based access for **Administrators**, **Faculty Members**, and **Stall Owners**, each with dedicated dashboards and functionality tailored to their responsibilities.

## 🚀 Core Modules

### 1. Smart Attendance Management System
AI-powered attendance tracking using computer vision.

**Key Features:**
- **Face Recognition Attendance**: Upload 5-10 photos per student for training
- **Live Webcam Attendance**: Real-time continuous face detection and marking
- **Photo-based Attendance**: Upload class photos to auto-mark attendance
- **Manual Attendance**: Traditional mark present/absent with one-click "Mark All Present"
- **Face Data Management**: Preview, delete per student, or bulk delete all face data
- **Accuracy Enhancements**:
  - Trains only on enrolled students for specific courses
  - Filters unusable images (no detectable face)
  - Ambiguity guard (refuses to mark if top matches are too close)
  - Strict threshold controls for photo mode
- **Reports & Analytics**: Attendance reports by course, section, and date range

**User Roles:** Faculty can create sessions, mark attendance; Admin can view all reports

---

### 2. Smart Food Stall Pre-Ordering System
Skip queues with advance meal booking and real-time order management.

**Key Features:**
- **Pre-Order Meals**: Students can order food in advance from multiple stalls
- **Vendor Dashboard**: Stall owners manage pending, ready, and completed orders
- **Order Status Tracking**: Real-time updates (Pending → Preparing → Ready → Completed/Missed)
- **Bulk Orders**: Support for large group orders
- **Menu Management**: Vendors can update menu items, prices, and availability
- **Order Notifications**: Students get updates when food is ready for pickup
- **Missed Order Handling**: Automatic flagging and re-scheduling options

**User Roles:** Students place orders; Stall Owners manage their stall dashboard

---

### 3. Campus Resource & Parameter Estimation
Data-driven resource optimization and campus analytics.

**Key Features:**
- **Resource Analytics**: Track classroom utilization, lab occupancy, and facility usage
- **Parameter Estimation**: Predict resource needs based on enrollment patterns
- **Visual Dashboards**: Charts and graphs for resource allocation insights
- **Optimization Suggestions**: AI-driven recommendations for better resource distribution
- **Historical Trends**: View resource usage patterns over time
- **Export Reports**: Generate PDF/Excel reports for administration

**User Roles:** Admin access to all analytics and reports

---

### 4. Make-Up Class & Remedial Module
Schedule and manage remedial classes for students who missed sessions.

**Key Features:**
- **Make-Up Class Scheduling**: Faculty can schedule remedial sessions
- **Student Eligibility Tracking**: Auto-identify students who need make-up classes
- **Attendance Integration**: Track attendance in make-up sessions separately
- **Conflict Detection**: Prevent scheduling conflicts with regular classes
- **Remedial Notifications**: Notify eligible students about upcoming make-up sessions
- **Progress Tracking**: Monitor which students have completed required remedial hours
- **Bulk Scheduling**: Schedule multiple make-up sessions at once

**User Roles:** Faculty schedule and manage; Students view and attend; Admin oversees

## 🛡️ Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **Administrator** | Full system access, all dashboards, user management, reports |
| **Faculty** | Attendance marking, make-up class scheduling, their assigned courses |
| **Stall Owner** | Vendor dashboard, order management, menu updates |
| **Student** | View attendance, pre-order food, view make-up class schedules |

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | Python, Django 5.x, Django REST Framework |
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript |
| **Computer Vision** | OpenCV, LBPH Face Recognizer, Haar Cascades, YuNet, SFace |
| **Database** | PostgreSQL (Production), SQLite (Development) |
| **AI/ML** | Face Recognition, Parameter Estimation Algorithms |
| **Deployment** | Render (Web Service), Render PostgreSQL |
| **Storage** | Persistent Disk for media files (face photos, models) |
