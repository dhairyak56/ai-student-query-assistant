import sys
import os
import requests
import json
import time
import subprocess

def check_python_version():
    """Check if Python version is compatible"""
    print("\n--- Checking Python Version ---")
    version = sys.version_info
    print(f"Python version: {sys.version}")
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ ERROR: Python 3.7 or higher is required")
        return False
    else:
        print("✅ Python version is compatible")
        return True

def check_required_packages():
    """Check if required packages are installed"""
    print("\n--- Checking Required Packages ---")
    required_packages = [
        "flask", 
        "flask-cors", 
        "google-generativeai", 
        "requests"
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            all_installed = False
    
    return all_installed

def check_api_connection():
    """Check if backend API is running"""
    print("\n--- Checking Backend API Connection ---")
    try:
        response = requests.get("http://127.0.0.1:5000/", timeout=5)
        print(f"❌ Response received but unexpected: Status code {response.status_code}")
        return False
    except requests.ConnectionError:
        try:
            # Try a simple POST request
            test_response = requests.post(
                "http://127.0.0.1:5000/query",
                json={"question": "test"},
                timeout=5
            )
            if test_response.status_code == 200:
                print(f"✅ Backend API is running (Status code: {test_response.status_code})")
                return True
            else:
                print(f"❌ Backend API returned error status: {test_response.status_code}")
                try:
                    error_msg = test_response.json().get('error', 'Unknown error')
                    print(f"   Error message: {error_msg}")
                except:
                    pass
                return False
        except requests.RequestException as e:
            print(f"❌ Backend API is not running or not accessible: {e}")
            return False
    except Exception as e:
        print(f"❌ Error checking API connection: {e}")
        return False

def test_simple_query():
    """Test a simple query to the backend"""
    print("\n--- Testing Query Functionality ---")
    try:
        response = requests.post(
            "http://127.0.0.1:5000/query",
            json={"question": "hello"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            if answer and len(answer) > 5:
                print(f"✅ Query successful. Received answer: {answer[:50]}...")
                return True
            else:
                print(f"❌ Query failed: Empty or too short answer")
                return False
        else:
            print(f"❌ Query failed: Status code {response.status_code}")
            try:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"   Error message: {error_msg}")
            except:
                pass
            return False
    except Exception as e:
        print(f"❌ Error testing simple query: {e}")
        return False

def start_backend():
    """Try to start the backend API"""
    print("\n--- Attempting to Start Backend API ---")
    try:
        # Start the backend in a new process
        process = subprocess.Popen(
            [sys.executable, "backend_api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        print("Waiting for backend to start (5 seconds)...")
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Backend API started successfully")
            return True, process
        else:
            stdout, stderr = process.communicate()
            print("❌ Backend API failed to start")
            print(f"STDOUT: {stdout[:500]}")
            print(f"STDERR: {stderr[:500]}")
            return False, None
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return False, None

def main():
    """Run all tests"""
    print("=== AI Student Query Assistant Troubleshooter ===")
    
    # Check Python version
    python_ok = check_python_version()
    if not python_ok:
        print("\n❌ Please upgrade your Python installation.")
        return
    
    # Check required packages
    packages_ok = check_required_packages()
    if not packages_ok:
        print("\n❌ Please install the missing packages using pip:")
        print("   pip install flask flask-cors google-generativeai requests")
        return
    
    # Check if backend is running
    backend_running = check_api_connection()
    backend_process = None
    
    # If backend is not running, try to start it
    if not backend_running:
        print("\nBackend API is not running. Attempting to start it...")
        backend_ok, backend_process = start_backend()
        if backend_ok:
            # Recheck API connection
            backend_running = check_api_connection()
    
    # Test a simple query if backend is running
    if backend_running:
        query_ok = test_simple_query()
        if query_ok:
            print("\n✅ The system appears to be working correctly!")
            print("   You can now start the frontend application:")
            print("   python ai_student_query_assistant.py")
        else:
            print("\n❌ The backend is running but query functionality failed.")
            print("   Check api.log for more detailed error information.")
    else:
        print("\n❌ Could not establish connection to the backend API.")
        print("   Please check api.log for error details.")
    
    # Clean up if we started the backend
    if backend_process and backend_process.poll() is None:
        print("\nClosing backend process...")
        backend_process.terminate()

if __name__ == "__main__":
    main()