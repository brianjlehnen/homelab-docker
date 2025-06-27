#!/usr/bin/env python3
"""
Enhanced Budget Automation Script with Advanced Features
Includes spending trends, alerts, forecasting, and interactive dashboard
YOUR WORKING VERSION + PREMIUM EMAIL STYLING
"""

import argparse
import os
import sys
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
import glob
import json
import sqlite3
from collections import defaultdict
import statistics

class EnhancedBudgetAutomation:
    def __init__(self, test_mode=False):
        """Initialize the enhanced budget automation system"""
        self.test_mode = test_mode
        self.setup_logging()
        self.load_environment()
        self.setup_categories()
        self.setup_database()
        
        if self.test_mode:
            logging.info("🧪 TEST MODE ENABLED - Emails will only be sent to primary user")
    
    def setup_logging(self):
        """Configure logging"""
        log_dir = "/app/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/budget_automation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def load_environment(self):
        """Load environment variables"""
        self.ynab_token = os.getenv('YNAB_API_TOKEN')
        self.budget_id = os.getenv('BUDGET_ID')
        self.gmail_email = os.getenv('GMAIL_EMAIL')
        self.gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        # New optional configuration
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')  # For Slack notifications
        self.spending_alert_threshold = float(os.getenv('SPENDING_ALERT_THRESHOLD', '90'))  # Alert at 90%
        
        if not all([self.ynab_token, self.budget_id, self.gmail_email, self.gmail_password]):
            raise ValueError("Missing required environment variables")
    
    def setup_categories(self):
            """Define category mappings and monthly targets - VARIABLE CATEGORIES ONLY"""
            self.category_mapping = {
                # Variable Categories Only
                "🥕  Groceries": "🥕 Groceries",
                "🛋️  Shopping": "🛒 Shopping & Personal",
                "🧘‍♀️  Personal Care": "🛒 Shopping & Personal", 
                "🍼  Baby Supplies": "🛒 Shopping & Personal",
                "🥯  Dining Out": "🍽️ Dining Out",
                "⛽️  Gas": "🚗 Transportation",
                "👩‍⚕️  Medical & Pediatric": "🏥 Services & Medical",
                "🦮  Pet Stuff": "🐕 Pet Care",
                "🔁   Subscriptions": "🎮 Entertainment & Tech",
                "🍿  Entertainment": "🎮 Entertainment & Tech",
                "🔨  Home Maintenance / HOA": "🔧 Home Maintenance",
                
                # REMOVED: All fixed costs (mortgage, utilities, daycare, etc.)
                # REMOVED: All irregular expenses (insurance, lawn service, etc.) 
                # REMOVED: All fund categories (home improvement, vacation, etc.)
            }
            
            # Monthly targets for variable categories only
            self.monthly_targets = {
                "🥕 Groceries": 900,
                "🛒 Shopping & Personal": 675,        # 600 shopping + 75 personal care
                "🍽️ Dining Out": 250,
                "🚗 Transportation": 150,             # Gas only
                "🏥 Services & Medical": 400,         # With buffer for unpredictability  
                "🐕 Pet Care": 300,                   # Pet stuff only (not insurance)
                "🎮 Entertainment & Tech": 125,
                "🔧 Home Maintenance": 101,           # Regular upkeep only
            }
            # Total: $2,801/month of truly variable expenses
    
    def setup_database(self):
        """Initialize SQLite database for historical data"""
        db_dir = "/app/config"
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "budget_history.db")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_spending (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    month_budget REAL NOT NULL,
                    percentage REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, category)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS spending_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def save_daily_data(self, spending_data, metrics):
        """Save today's spending data to database"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            for category, data in metrics.items():
                conn.execute("""
                    INSERT OR REPLACE INTO daily_spending 
                    (date, category, amount, month_budget, percentage)
                    VALUES (?, ?, ?, ?, ?)
                """, (today, category, data['spent'], data['target'], data['percentage']))
    
    def get_historical_data(self, days=30):
        """Get historical spending data for trends"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT date, category, amount, percentage 
                FROM daily_spending 
                WHERE date >= ? 
                ORDER BY date ASC
            """, (cutoff_date,))
            
            data = defaultdict(list)
            for row in cursor.fetchall():
                date, category, amount, percentage = row
                data[category].append({
                    'date': date,
                    'amount': amount,
                    'percentage': percentage
                })
            
            return dict(data)
    
    def calculate_spending_trends(self, historical_data):
        """Calculate spending trends and predictions"""
        trends = {}
        
        for category, data_points in historical_data.items():
            if len(data_points) < 7:  # Need at least a week of data
                continue
                
            amounts = [point['amount'] for point in data_points[-14:]]  # Last 2 weeks
            percentages = [point['percentage'] for point in data_points[-14:]]
            
            # Calculate trend (simple linear regression slope)
            if len(amounts) >= 2:
                x_values = list(range(len(amounts)))
                n = len(amounts)
                sum_x = sum(x_values)
                sum_y = sum(amounts)
                sum_xy = sum(x * y for x, y in zip(x_values, amounts))
                sum_x2 = sum(x * x for x in x_values)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                # Trend analysis
                if slope > 5:  # Increasing by more than $5/day
                    trend = "📈 Increasing"
                    trend_color = "#dc3545"
                elif slope < -5:  # Decreasing by more than $5/day
                    trend = "📉 Decreasing"  
                    trend_color = "#28a745"
                else:
                    trend = "➡️ Stable"
                    trend_color = "#6c757d"
                
                # Simple forecast for month end
                days_left = 30 - datetime.now().day
                projected_additional = slope * days_left
                current_amount = amounts[-1] if amounts else 0
                projected_total = current_amount + max(0, projected_additional)
                
                trends[category] = {
                    'trend': trend,
                    'trend_color': trend_color,
                    'slope': slope,
                    'projected_total': projected_total,
                    'avg_daily': statistics.mean(amounts[-7:]) if len(amounts) >= 7 else 0
                }
        
        return trends
    
    def check_spending_alerts(self, metrics):
        """Check for spending alerts and save them"""
        alerts = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            for category, data in metrics.items():
                percentage = data['percentage']
                
                # High spending alert
                if percentage >= self.spending_alert_threshold and percentage < 100:
                    alert_msg = f"{category} is at {percentage:.0f}% of monthly budget"
                    alerts.append({
                        'type': 'high_spending',
                        'category': category,
                        'message': alert_msg,
                        'severity': 'warning'
                    })
                    
                    conn.execute("""
                        INSERT INTO spending_alerts (date, category, alert_type, message)
                        VALUES (?, ?, ?, ?)
                    """, (today, category, 'high_spending', alert_msg))
                
                # Over budget alert
                elif percentage >= 100:
                    alert_msg = f"{category} is OVER BUDGET at {percentage:.0f}%"
                    alerts.append({
                        'type': 'over_budget',
                        'category': category,
                        'message': alert_msg,
                        'severity': 'danger'
                    })
                    
                    conn.execute("""
                        INSERT INTO spending_alerts (date, category, alert_type, message)
                        VALUES (?, ?, ?, ?)
                    """, (today, category, 'over_budget', alert_msg))
        
        return alerts
    
    def send_slack_notification(self, alerts):
        """Send Slack notification for critical alerts"""
        if not self.webhook_url or not alerts:
            return
        
        critical_alerts = [alert for alert in alerts if alert['severity'] == 'danger']
        if not critical_alerts:
            return
        
        try:
            message = {
                "text": "🚨 Budget Alert: Categories Over Budget",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🚨 Budget Alerts*\n" + "\n".join([f"• {alert['message']}" for alert in critical_alerts])
                        }
                    }
                ]
            }
            
            response = requests.post(self.webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logging.info("✅ Slack notification sent for critical alerts")
            
        except Exception as e:
            logging.error(f"❌ Failed to send Slack notification: {e}")
    
    def get_recipients(self):
        """Get email recipients based on mode"""
        if self.test_mode:
            recipients = ["blehnen@gmail.com"]
            logging.info(f"🧪 Test mode: Sending only to {recipients[0]}")
        else:
            recipients = ["jenlanser@gmail.com", "blehnen@gmail.com"]
            logging.info(f"📧 Normal mode: Sending to {len(recipients)} recipients")
        
        return recipients
    
    def get_subject_line(self):
        """Get email subject with house icon and test mode indicator"""
        base_subject = f"🏠 Weekly Budget Report - {datetime.now().strftime('%B %d, %Y')}"
        
        if self.test_mode:
            return f"[TEST] {base_subject}"
        else:
            return base_subject
    
    def fetch_ynab_data(self):
        """Fetch transaction data from YNAB API"""
        logging.info("🔄 Fetching YNAB transaction data...")
        
        # Get current month's start date
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        since_date = start_of_month.strftime('%Y-%m-%d')
        
        url = f"https://api.ynab.com/v1/budgets/{self.budget_id}/transactions"
        headers = {"Authorization": f"Bearer {self.ynab_token}"}
        params = {"since_date": since_date}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            transactions = response.json()['data']['transactions']
            spending_data = self.process_transactions(transactions)
            
            logging.info(f"✅ Successfully processed {len(transactions)} transactions")
            return spending_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error fetching YNAB data: {e}")
            raise
    
    def process_transactions(self, transactions):
        """Process transactions and categorize spending"""
        spending_by_category = {}
        
        for transaction in transactions:
            if transaction['amount'] < 0:  # Only outflows (spending)
                category_name = transaction.get('category_name', 'Uncategorized')
                mapped_category = self.category_mapping.get(category_name, category_name)
                
                if mapped_category in self.monthly_targets:
                    amount = abs(transaction['amount']) / 1000  # Convert from milliunits
                    spending_by_category[mapped_category] = spending_by_category.get(mapped_category, 0) + amount
        
        return spending_by_category
    
    def calculate_metrics(self, spending_data):
        """Calculate metrics for each category"""
        metrics = {}
        
        for category, target in self.monthly_targets.items():
            spent = spending_data.get(category, 0)
            percentage = (spent / target * 100) if target > 0 else 0
            
            # Determine status
            if percentage > 100:
                status = "🚨 Over Budget"
                status_color = "#dc3545"
            elif percentage > 90:
                status = "⚠️ Close to Limit"
                status_color = "#ffc107"
            else:
                status = "✅ On Track"
                status_color = "#28a745"
            
            metrics[category] = {
                'spent': spent,
                'target': target,
                'percentage': percentage,
                'status': status,
                'status_color': status_color
            }
        
        return metrics
    
    def generate_enhanced_html_email(self, spending_data, trends, alerts):
        """Generate beautiful, cohesive HTML email with final polished design"""
        metrics = self.calculate_metrics(spending_data)
        today = datetime.now()
        month_name = today.strftime("%B")
        day = today.day
        
        total_spent = sum(spending_data.values())
        total_budget = sum(self.monthly_targets.values())
        overall_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        sorted_metrics = sorted(metrics.items(), key=lambda x: x[1]['percentage'], reverse=True)
        
        # Clean test mode banner
        test_banner = ""
        if self.test_mode:
            test_banner = f"""
            <div style="background: #fef3c7; border-radius: 8px; padding: 12px; margin-bottom: 24px; text-align: center;">
                <span style="color: #92400e; font-weight: 600;">🧪 TEST MODE</span>
            </div>
            """
        
        # Compact grey alert cards with red accents
        alerts_section = ""
        if alerts:
            alert_items = ""
            for alert in alerts:
                # Get category info for proper icon
                category = alert['category']
                overage = 0
                
                # Calculate overage amount
                if category in metrics:
                    spent = metrics[category]['spent']
                    target = metrics[category]['target']
                    if spent > target:
                        overage = spent - target
                
                # Map to proper category icon
                category_icons = {
                    "🏠 Housing & Utilities": "🏠",
                    "🥕 Groceries": "🥕", 
                    "🍽️ Dining Out": "🍽️",
                    "🛒 Shopping & Personal": "🛒",
                    "👶 Childcare & Education": "👶",
                    "🐕 Pet Care": "🐕",
                    "🏥 Services & Medical": "🏥",
                    "🚗 Transportation": "🚗",
                    "🍿 Entertainment & Tech": "🍿",
                    "💰 Financial": "💰"
                }
                
                icon = category_icons.get(category, "⚠️")
                
                alert_items += f"""
                <div style="background: #f9fafb; border-radius: 6px; padding: 12px 16px; border-left: 4px solid #dc2626;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="vertical-align: middle;">
                                <span style="color: #1f2937; font-weight: 600;">{category}</span>
                            </td>
                            <td style="text-align: right; vertical-align: middle;">
                                <span style="color: #dc2626; font-weight: 700; font-size: 14px;">+${overage:,.0f}</span>
                            </td>
                        </tr>
                    </table>
                </div>
                """
            
            alerts_section = f"""
            <div style="margin-bottom: 32px;">
                <h3 style="color: #1f2937; font-size: 18px; font-weight: 700; margin-bottom: 16px; text-align: center;">⚠️ Budget Alerts</h3>
                <div style="display: grid; gap: 8px;">
                    {alert_items}
                </div>
            </div>
            """
        
        # Beautiful category cards with proper icons
        category_cards = ""
        for category, data in sorted_metrics:
            progress_width = min(data['percentage'], 100)
            
            # Category icon mapping
            category_icons = {
                "🏠 Housing & Utilities": "🏠",
                "🥕 Groceries": "🥕", 
                "🍽️ Dining Out": "🍽️",
                "🛒 Shopping & Personal": "🛒",
                "👶 Childcare & Education": "👶",
                "🐕 Pet Care": "🐕",
                "🏥 Services & Medical": "🏥",
                "🚗 Transportation": "🚗",
                "🍿 Entertainment & Tech": "🍿",
                "💰 Financial": "💰"
            }
            
            icon = category_icons.get(category, "📊")
            
            # Color scheme based on status
            if data['percentage'] > 100:
                card_bg = "#fef2f2"
                border_color = "#dc2626"
                progress_bg = "#fee2e2"
                text_color = "#dc2626"
            elif data['percentage'] > 90:
                card_bg = "#fffbeb"
                border_color = "#d97706"
                progress_bg = "#fef3c7"
                text_color = "#d97706"
            else:
                card_bg = "#f0fdf4"
                border_color = "#059669"
                progress_bg = "#dcfce7"
                text_color = "#059669"
            
            # Clean trend info (if available)
            trend_info = ""
            if category in trends:
                trend_data = trends[category]
                if trend_data['slope'] > 5:
                    trend_info = f"<span style='color: #dc2626; font-size: 12px;'> 📈 Trending up</span>"
                elif trend_data['slope'] < -5:
                    trend_info = f"<span style='color: #059669; font-size: 12px;'> 📉 Trending down</span>"
            
            category_cards += f"""
            <div style="background: {card_bg}; border-radius: 8px; padding: 20px; margin-bottom: 12px; border-left: 4px solid {border_color};">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="vertical-align: middle; width: 70%;">
                            <div style="font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 4px;">
                                {category}
                            </div>
                            <div style="color: #6b7280; font-size: 14px;">
                                ${data['spent']:,.0f} of ${data['target']:,.0f}{trend_info}
                            </div>
                        </td>
                        <td style="text-align: right; vertical-align: middle; width: 30%;">
                            <div style="font-size: 24px; font-weight: 800; color: {text_color}; margin-bottom: 6px;">
                                {data['percentage']:.0f}%
                            </div>
                            <div style="width: 80px; height: 6px; background: {progress_bg}; border-radius: 3px; margin-left: auto;">
                                <div style="width: {progress_width}%; height: 100%; background: {text_color}; border-radius: 3px;"></div>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            """
        
        # Clean insights section
        insights_content = f"""
        <div style="color: #1e40af; font-weight: 700; margin-bottom: 8px;">📊 Budget Status</div>
        <div style="color: #4b5563; line-height: 1.5;">
            You're <strong>{overall_percentage:.1f}%</strong> through your monthly budget on day <strong>{day}</strong> of {month_name}. 
            {'🎯 Great pacing!' if overall_percentage <= (day/30*100 + 5) else '⚠️ Consider reviewing spending in over-budget categories.'}
        </div>
        """
        
        # Add trend insights if available
        if trends:
            high_trend_categories = [cat for cat, data in trends.items() if data['slope'] > 5]
            if high_trend_categories:
                insights_content += f"""
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(59, 130, 246, 0.2);">
                    <div style="color: #dc2626; font-weight: 600; margin-bottom: 6px;">📈 Spending Trends</div>
                    <div style="color: #4b5563; line-height: 1.5;">
                        Categories with increasing spending: <strong style="color: #dc2626;">{', '.join(high_trend_categories)}</strong>
                    </div>
                </div>
                """

        # Beautiful, cohesive HTML email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Budget Report</title>
</head>
<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; line-height: 1.4;">
    
    <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
        
        <!-- Beautiful Header -->
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 32px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 700;">🏠 Weekly Budget Report</h1>
            <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{month_name} {today.day}, {today.year} • Day {day}</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 32px;">
            
            {test_banner}
            
            <!-- Summary Cards -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 32px;">
                <div style="text-align: center; padding: 20px; background: #f0fdf4; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: 800; color: #166534;">${total_budget:,.0f}</div>
                    <div style="font-size: 12px; color: #166534; font-weight: 600;">BUDGET</div>
                </div>
                <div style="text-align: center; padding: 20px; background: #fffbeb; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: 800; color: #92400e;">${total_spent:,.0f}</div>
                    <div style="font-size: 12px; color: #92400e; font-weight: 600;">SPENT</div>
                </div>
                <div style="text-align: center; padding: 20px; background: {'#f0fdf4' if total_budget - total_spent > 0 else '#fef2f2'}; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: 800; color: {'#166534' if total_budget - total_spent > 0 else '#991b1b'};">${total_budget - total_spent:,.0f}</div>
                    <div style="font-size: 12px; color: {'#166534' if total_budget - total_spent > 0 else '#991b1b'}; font-weight: 600;">REMAINING</div>
                </div>
            </div>
            
            {alerts_section}
            
            <!-- Category Breakdown -->
            <div style="margin-bottom: 32px;">
                <h3 style="color: #1f2937; font-size: 18px; font-weight: 700; margin-bottom: 16px; text-align: center;">📋 Category Breakdown</h3>
                {category_cards}
            </div>
            
            <!-- Insights -->
            <div style="background: #eff6ff; border-radius: 8px; border-left: 4px solid #3b82f6; padding: 20px;">
                {insights_content}
            </div>
            
        </div>
        
        <!-- Footer -->
        <div style="background: #374151; color: white; padding: 20px; text-align: center;">
            <p style="margin: 0; font-size: 12px; opacity: 0.9; margin-bottom: 12px;">
                Generated {today.strftime("%B %d, %Y at %I:%M %p")}{'  •  TEST MODE' if self.test_mode else ''}
            </p>
            <a href="https://budget.lab1830.com" style="display: inline-block; background: #4f46e5; color: white; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 12px;">
                🚀 View Dashboard
            </a>
        </div>
        
    </div>
    
</body>
</html>
        """
        
        return html
    
    def send_email(self, html_content, spending_data):
        """Send email with enhanced budget report"""
        recipients = self.get_recipients()
        subject = self.get_subject_line()
        
        total_spent = sum(spending_data.values())
        total_budget = sum(self.monthly_targets.values())
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.gmail_email
        msg['To'] = ', '.join(recipients)
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                server.sendmail(self.gmail_email, recipients, msg.as_string())
            
            logging.info(f"✅ Enhanced email sent successfully to {len(recipients)} recipient{'s' if len(recipients) > 1 else ''}")
            
        except Exception as e:
            logging.error(f"❌ Failed to send email: {e}")
            raise
    
    def save_html_report(self, html_content):
        """Save HTML report to file with test mode isolation"""
        report_dir = "/app/reports"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.test_mode:
            # Save test reports in separate subdirectory
            test_dir = os.path.join(report_dir, "test")
            os.makedirs(test_dir, exist_ok=True)
            filename = f"test_budget_report_{timestamp}.html"
            filepath = os.path.join(test_dir, filename)
            logging.info(f"💾 Test HTML report saved: test/{filename}")
        else:
            # Save production reports normally
            filename = f"enhanced_budget_report_{timestamp}.html"
            filepath = os.path.join(report_dir, filename)
            logging.info(f"💾 Enhanced HTML report saved: {filename}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filename
    
    def export_data_json(self, spending_data, metrics, trends, alerts):
        """Export current data as JSON for API access with test mode isolation"""
        export_dir = "/app/reports"
        os.makedirs(export_dir, exist_ok=True)
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'spending_data': spending_data,
            'metrics': metrics,
            'trends': trends,
            'alerts': alerts,
            'test_mode': self.test_mode,
            'totals': {
                'spent': sum(spending_data.values()),
                'budget': sum(self.monthly_targets.values()),
                'remaining': sum(self.monthly_targets.values()) - sum(spending_data.values())
            }
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.test_mode:
            # Save test data in separate subdirectory without affecting production
            test_dir = os.path.join(export_dir, "test")
            os.makedirs(test_dir, exist_ok=True)
            
            # Save test version with timestamp
            test_file = os.path.join(test_dir, f"test_budget_data_{timestamp}.json")
            with open(test_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logging.info(f"📊 Test budget data exported to test/test_budget_data_{timestamp}.json")
            return test_file
        else:
            # Save production data normally
            # Save latest data (overwrites previous)
            latest_file = os.path.join(export_dir, "latest_budget_data.json")
            with open(latest_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            # Save timestamped version
            timestamped_file = os.path.join(export_dir, f"budget_data_{timestamp}.json")
            with open(timestamped_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logging.info(f"📊 Production budget data exported to JSON")
            return latest_file
    
    def cleanup_old_files(self):
        """Clean up files older than 3 months, with special handling for test files"""
        cutoff_date = datetime.now() - timedelta(days=90)
        test_cutoff_date = datetime.now() - timedelta(days=7)  # Clean test files after 1 week
        
        for directory in ["/app/reports", "/app/logs"]:
            # Clean regular files (3 months)
            pattern = os.path.join(directory, "*")
            files = glob.glob(pattern)
            
            cleaned_count = 0
            for file_path in files:
                if (os.path.isfile(file_path) and 
                    not file_path.endswith("latest_budget_data.json") and
                    not "/test/" in file_path):  # Skip test directory files here
                    
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logging.info(f"🧹 Cleaned up {cleaned_count} old files from {directory}")
            
            # Clean test files separately (1 week retention)
            test_dir = os.path.join(directory, "test")
            if os.path.exists(test_dir):
                test_pattern = os.path.join(test_dir, "*")
                test_files = glob.glob(test_pattern)
                
                test_cleaned_count = 0
                for file_path in test_files:
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < test_cutoff_date:
                            os.remove(file_path)
                            test_cleaned_count += 1
                
                if test_cleaned_count > 0:
                    logging.info(f"🧹 Cleaned up {test_cleaned_count} old test files from {os.path.basename(directory)}")
                
                # Remove empty test directory
                if not os.listdir(test_dir):
                    os.rmdir(test_dir)
                    logging.info(f"🧹 Removed empty test directory from {os.path.basename(directory)}")
            
            if cleaned_count == 0 and (not os.path.exists(test_dir) or len(glob.glob(os.path.join(test_dir, "*"))) == 0):
                logging.info(f"🧹 No old files found for cleanup in {os.path.basename(directory)}")
    
    def run(self):
        """Main execution function with enhanced features"""
        try:
            mode_text = "🧪 test mode" if self.test_mode else "📧 normal mode"
            logging.info(f"🚀 Starting enhanced budget automation ({mode_text})")
            
            # Fetch and process data
            spending_data = self.fetch_ynab_data()
            metrics = self.calculate_metrics(spending_data)
            
            # Save current data to database
            self.save_daily_data(spending_data, metrics)
            
            # Get historical data and calculate trends
            historical_data = self.get_historical_data(30)
            trends = self.calculate_spending_trends(historical_data)
            
            # Check for alerts
            alerts = self.check_spending_alerts(metrics)
            
            # Send Slack notifications for critical alerts
            self.send_slack_notification(alerts)
            
            # Generate and send enhanced report
            html_content = self.generate_enhanced_html_email(spending_data, trends, alerts)
            self.send_email(html_content, spending_data)
            
            # Save reports and export data
            self.save_html_report(html_content)
            self.export_data_json(spending_data, metrics, trends, alerts)
            self.cleanup_old_files()
            
            # Final summary
            total_spent = sum(spending_data.values())
            total_budget = sum(self.monthly_targets.values())
            percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
            
            logging.info(f"✅ Enhanced budget automation completed successfully!")
            logging.info(f"📊 Budget Summary: ${total_spent:,.0f} spent of ${total_budget:,.0f} budget ({percentage:.1f}%)")
            logging.info(f"🚨 Alerts generated: {len(alerts)}")
            logging.info(f"📈 Categories with trend data: {len(trends)}")
            
        except Exception as e:
            logging.error(f"❌ Enhanced budget automation failed: {e}")
            raise

def main():
    """Main function with enhanced argument parsing"""
    parser = argparse.ArgumentParser(description='Enhanced YNAB Budget Automation Script')
    parser.add_argument('--test', action='store_true', 
                       help='Run in test mode (send emails only to primary user)')
    parser.add_argument('--export-only', action='store_true',
                       help='Only export data to JSON without sending emails')
    
    args = parser.parse_args()
    
    # Run the enhanced automation
    automation = EnhancedBudgetAutomation(test_mode=args.test)
    
    if args.export_only:
        # Quick data export mode
        spending_data = automation.fetch_ynab_data()
        metrics = automation.calculate_metrics(spending_data)
        automation.save_daily_data(spending_data, metrics)
        historical_data = automation.get_historical_data(30)
        trends = automation.calculate_spending_trends(historical_data)
        alerts = automation.check_spending_alerts(metrics)
        automation.export_data_json(spending_data, metrics, trends, alerts)
        logging.info("📊 Data export completed")
    else:
        automation.run()

if __name__ == "__main__":
    main()