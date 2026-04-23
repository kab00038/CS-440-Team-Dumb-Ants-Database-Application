# IT Asset Management System - Team Dumb Ants

An IT Asset Management Database Management System (DBMS) application developed for **CS 440 (Spring 2026)**.

## 🚀 Overview

This application provides a robust solution for tracking and managing IT assets within an organization. It allows users to systematically manage hardware, software licenses, database connections, and asset assignments efficiently.

## 🛠️ Technology Stack

* **Language:** Python
* **Database:** MySQL
* **Database Hosting:** [Aiven](https://aiven.io/) (Fully managed cloud database hosting)

## ⚙️ Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd CS-440-Team-Dumb-Ants-Database-Application
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Configuration:**
   * The database is hosted remotely on Aiven. 
   * Ensure you have the required connection URI and credentials configured in your environment variables or configuration file before starting the application.

## 🏃‍♂️ Running the Application

### 🔄 After Pulling New Commits

After pulling new commits, always reinstall dependencies before running the app in case new libraries were added:

```bash
pip install -r requirements.txt
```

```bash
streamlit run src/main.py
```

## 👥 Team
* **Team Dumb Ants** - CS 440 Spring 2026
