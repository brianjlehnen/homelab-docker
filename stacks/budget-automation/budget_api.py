#!/usr/bin/env python3
"""
Simple Budget API Service
Provides REST endpoints for budget data access
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BudgetAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.data_dir = "/app/reports"
        self.db_path = "/app/config/budget_history.db"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == "/api/current":
                self.serve_current_data()
            elif path == "/api/history":
                days = int(query_params.get('days', [30])[0])
                self.serve_historical_data(days)
            elif path == "/api/alerts":
                self.serve_alerts()
            elif path == "/api/trends":
                self.serve_trends()
            elif path == "/api/health":
                self.serve_health()
            else:
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            logger.error(f"API Error: {e}")
            self.send_error(500, str(e))
    
    def serve_current_data(self):
        """Serve current budget data"""
        try:
            latest_file = os.path.join(self.data_dir, "latest_budget_data.json")
            
            if not os.path.exists(latest_file):
                self.send_error(404, "No current data available")
                return
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            self.send_json_response(data)
            
        except Exception as e:
            logger.error(f"Error serving current data: {e}")
            self.send_error(500, "Failed to load current data")
    
    def serve_historical_data(self, days=30):
        """Serve historical spending data"""
        if not os.path.exists(self.db_path):
            self.send_error(404, "No historical data available")
            return
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT date, category, amount, percentage, month_budget
                    FROM daily_spending 
                    WHERE date >= ? 
                    ORDER BY date ASC, category ASC
                """, (cutoff_date,))
                
                rows = cursor.fetchall()
                
                # Format data
                data = []
                for row in rows:
                    data.append({
                        'date': row[0],
                        'category': row[1],
                        'amount': row[2],
                        'percentage': row[3],
                        'month_budget': row[4]
                    })
                
                response = {
                    'days': days,
                    'start_date': cutoff_date,
                    'data': data,
                    'count': len(data)
                }
                
                self.send_json_response(response)
                
        except Exception as e:
            logger.error(f"Error serving historical data: {e}")
            self.send_error(500, "Failed to load historical data")
    
    def serve_alerts(self):
        """Serve recent alerts"""
        if not os.path.exists(self.db_path):
            self.send_error(404, "No alerts data available")
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT date, category, alert_type, message, created_at
                    FROM spending_alerts 
                    WHERE date >= date('now', '-7 days')
                    ORDER BY created_at DESC
                    LIMIT 50
                """)
                
                rows = cursor.fetchall()
                
                data = []
                for row in rows:
                    data.append({
                        'date': row[0],
                        'category': row[1],
                        'alert_type': row[2],
                        'message': row[3],
                        'created_at': row[4]
                    })
                
                response = {
                    'alerts': data,
                    'count': len(data)
                }
                
                self.send_json_response(response)
                
        except Exception as e:
            logger.error(f"Error serving alerts: {e}")
            self.send_error(500, "Failed to load alerts")
    
    def serve_trends(self):
        """Serve spending trends analysis"""
        try:
            latest_file = os.path.join(self.data_dir, "latest_budget_data.json")
            
            if not os.path.exists(latest_file):
                self.send_error(404, "No trend data available")
                return
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            trends = data.get('trends', {})
            
            response = {
                'trends': trends,
                'generated_at': data.get('timestamp'),
                'categories_analyzed': len(trends)
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            logger.error(f"Error serving trends: {e}")
            self.send_error(500, "Failed to load trends")
    
    def serve_health(self):
        """Health check endpoint"""
        try:
            latest_file = os.path.join(self.data_dir, "latest_budget_data.json")
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'data_available': os.path.exists(latest_file),
                'database_available': os.path.exists(self.db_path)
            }
            
            if health_data['data_available']:
                stat = os.stat(latest_file)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                age_hours = (datetime.now() - last_modified).total_seconds() / 3600
                health_data['data_age_hours'] = round(age_hours, 2)
                health_data['data_fresh'] = age_hours < 24
            
            self.send_json_response(health_data)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            self.send_error(500, "Health check failed")
    
    def send_json_response(self, data):
        """Send JSON response with CORS headers"""
        response_data = json.dumps(data, indent=2)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        self.wfile.write(response_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        logger.info(f"{self.address_string()} - {format % args}")

def run_server():
    """Run the API server"""
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, BudgetAPIHandler)
    
    logger.info("Budget API Server starting on port 8000...")
    logger.info("Available endpoints:")
    logger.info("  GET /api/current - Current budget data")
    logger.info("  GET /api/history?days=30 - Historical data")
    logger.info("  GET /api/alerts - Recent alerts")
    logger.info("  GET /api/trends - Spending trends")
    logger.info("  GET /api/health - Health check")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Budget API Server...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()