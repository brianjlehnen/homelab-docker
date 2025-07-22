#!/usr/bin/env python3
"""
Test Data Management Script
Helps manage test vs production data and cleanup
"""

import os
import glob
import json
import argparse
from datetime import datetime, timedelta

def clean_test_data(reports_dir="/app/reports"):
    """Clean up all test data"""
    test_dir = os.path.join(reports_dir, "test")
    
    if not os.path.exists(test_dir):
        print("✅ No test directory found - nothing to clean")
        return
    
    test_files = glob.glob(os.path.join(test_dir, "*"))
    
    if not test_files:
        print("✅ Test directory is already empty")
        os.rmdir(test_dir)
        print("🗑️ Removed empty test directory")
        return
    
    removed_count = 0
    for file_path in test_files:
        if os.path.isfile(file_path):
            os.remove(file_path)
            removed_count += 1
            print(f"🗑️ Removed: {os.path.basename(file_path)}")
    
    # Remove the test directory itself
    os.rmdir(test_dir)
    print(f"✅ Cleaned up {removed_count} test files and removed test directory")

def check_latest_data_source(reports_dir="/app/reports"):
    """Check if latest data is from test mode"""
    latest_file = os.path.join(reports_dir, "latest_budget_data.json")
    
    if not os.path.exists(latest_file):
        print("⚠️ No latest_budget_data.json found")
        return False
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        is_test = data.get('test_mode', False)
        timestamp = data.get('timestamp', 'Unknown')
        
        if is_test:
            print(f"🧪 WARNING: Latest data is from TEST MODE (generated: {timestamp})")
            print("   The dashboard is currently showing test data!")
            return True
        else:
            print(f"✅ Latest data is from PRODUCTION MODE (generated: {timestamp})")
            return False
            
    except Exception as e:
        print(f"❌ Error reading latest data: {e}")
        return False

def restore_production_data(reports_dir="/app/reports"):
    """Find and restore the most recent production data"""
    # Look for production data files
    pattern = os.path.join(reports_dir, "budget_data_*.json")
    prod_files = []
    
    for file_path in glob.glob(pattern):
        if "/test/" not in file_path:  # Skip test files
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if not data.get('test_mode', False):
                    file_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                    prod_files.append((file_time, file_path, data))
            except:
                continue
    
    if not prod_files:
        print("❌ No production data files found")
        return False
    
    # Sort by timestamp and get the most recent
    prod_files.sort(key=lambda x: x[0], reverse=True)
    latest_prod_time, latest_prod_file, latest_prod_data = prod_files[0]
    
    # Restore as latest
    latest_file = os.path.join(reports_dir, "latest_budget_data.json")
    
    with open(latest_file, 'w') as f:
        json.dump(latest_prod_data, f, indent=2)
    
    print(f"✅ Restored production data from {latest_prod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Source: {os.path.basename(latest_prod_file)}")
    return True

def list_data_files(reports_dir="/app/reports"):
    """List all data files with their mode and timestamps"""
    print("\n📊 Budget Data Files:")
    print("=" * 60)
    
    # Check latest file
    latest_file = os.path.join(reports_dir, "latest_budget_data.json")
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            mode = "TEST" if data.get('test_mode', False) else "PROD"
            timestamp = data.get('timestamp', 'Unknown')
            print(f"📌 LATEST: {mode} mode - {timestamp}")
        except:
            print("📌 LATEST: Error reading file")
    
    print("\n🗂️ Historical Files:")
    
    # List all timestamped files
    pattern = os.path.join(reports_dir, "budget_data_*.json")
    files_info = []
    
    for file_path in glob.glob(pattern):
        if "/test/" not in file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                mode = "TEST" if data.get('test_mode', False) else "PROD"
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                files_info.append((timestamp, os.path.basename(file_path), mode))
            except:
                continue
    
    # List test files
    test_dir = os.path.join(reports_dir, "test")
    if os.path.exists(test_dir):
        for file_path in glob.glob(os.path.join(test_dir, "*.json")):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                files_info.append((timestamp, f"test/{os.path.basename(file_path)}", "TEST"))
            except:
                continue
    
    # Sort by timestamp
    files_info.sort(key=lambda x: x[0], reverse=True)
    
    for timestamp, filename, mode in files_info[:10]:  # Show last 10
        age = datetime.now() - timestamp.replace(tzinfo=None)
        age_str = f"{age.days}d" if age.days > 0 else f"{age.seconds//3600}h"
        print(f"   {mode}: {filename} ({age_str} ago)")
    
    if len(files_info) > 10:
        print(f"   ... and {len(files_info) - 10} more files")

def main():
    parser = argparse.ArgumentParser(description='Budget Test Data Management')
    parser.add_argument('--clean-test', action='store_true', 
                       help='Remove all test data files')
    parser.add_argument('--check-latest', action='store_true',
                       help='Check if latest data is from test mode')
    parser.add_argument('--restore-prod', action='store_true',
                       help='Restore latest production data as current')
    parser.add_argument('--list', action='store_true',
                       help='List all data files')
    parser.add_argument('--reports-dir', default='/app/reports',
                       help='Reports directory path')
    
    args = parser.parse_args()
    
    if not any([args.clean_test, args.check_latest, args.restore_prod, args.list]):
        # Default action: check status
        print("🔍 Budget Data Status Check")
        print("=" * 40)
        is_test = check_latest_data_source(args.reports_dir)
        
        if is_test:
            print("\n💡 Recommendations:")
            print("   • Run with --restore-prod to restore production data")
            print("   • Run with --clean-test to remove test files")
        
        list_data_files(args.reports_dir)
        return
    
    if args.clean_test:
        print("🧹 Cleaning test data...")
        clean_test_data(args.reports_dir)
    
    if args.check_latest:
        check_latest_data_source(args.reports_dir)
    
    if args.restore_prod:
        print("🔄 Restoring production data...")
        if restore_production_data(args.reports_dir):
            print("✅ Production data restored successfully")
        else:
            print("❌ Failed to restore production data")
    
    if args.list:
        list_data_files(args.reports_dir)

if __name__ == "__main__":
    main()