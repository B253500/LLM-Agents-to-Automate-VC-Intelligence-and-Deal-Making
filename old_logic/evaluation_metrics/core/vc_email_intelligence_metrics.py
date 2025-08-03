"""
VC Email Intelligence Evaluation Metrics
Tracks automated metrics for VC email intelligence system performance
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class EmailProcessingMetrics:
    """Individual email processing performance metrics"""
    email_id: str
    processing_time_seconds: float
    success: bool
    error_type: str = None
    response_time_seconds: float = 0.0
    sections_processed: int = 0
    data_extracted: bool = False

@dataclass
class VCEmailIntelligenceMetrics:
    """Container for all VC email intelligence evaluation metrics"""
    
    # System performance metrics
    agent_success_rate: float  # Percentage of successful email processing
    average_response_time: float  # Average time to respond to emails (seconds)
    system_uptime: float  # Percentage of time system is available
    error_rate: float  # Percentage of processing errors
    
    # Volume and throughput metrics
    daily_email_volume: int  # Number of emails processed per day
    weekly_email_volume: int  # Number of emails processed per week
    total_emails_processed: int  # Total emails processed
    
    # Performance metrics
    fastest_response_time: float  # Fastest email response time
    slowest_response_time: float  # Slowest email response time
    average_processing_time: float  # Average email processing time
    
    # Error tracking
    total_errors: int  # Total number of errors
    error_types: Dict[str, int]  # Breakdown of error types
    network_errors: int  # Network-related errors
    parsing_errors: int  # Data parsing errors
    api_errors: int  # API-related errors
    
    # System health metrics
    memory_usage_mb: float  # Memory consumption
    cpu_usage_percent: float  # CPU utilization
    active_connections: int  # Number of active connections
    
    # Timestamp
    evaluation_timestamp: str

class VCEmailIntelligenceEvaluator:
    """Evaluates VC email intelligence system performance"""
    
    def __init__(self):
        self.start_time = None
        self.email_logs = {}
        self.system_logs = {
            "start_time": None,
            "uptime_checks": [],
            "error_counts": {},
            "performance_metrics": {}
        }
        self.daily_stats = {
            "emails_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "total_response_time": 0.0
        }
    
    def start_evaluation(self):
        """Start timing the email intelligence evaluation"""
        self.start_time = time.time()
        self.system_logs["start_time"] = time.time()
        self.email_logs = {}
    
    def log_email_processing_start(self, email_id: str):
        """Log the start of email processing"""
        self.email_logs[email_id] = {
            "start_time": time.time(),
            "processing_time": 0.0,
            "success": False,
            "error_type": None,
            "response_time": 0.0,
            "sections_processed": 0,
            "data_extracted": False
        }
    
    def log_email_processing_end(self, email_id: str, success: bool, 
                               processing_time: float, error_type: str = None,
                               response_time: float = 0.0, sections_processed: int = 0,
                               data_extracted: bool = False):
        """Log the end of email processing"""
        if email_id in self.email_logs:
            self.email_logs[email_id].update({
                "processing_time": processing_time,
                "success": success,
                "error_type": error_type,
                "response_time": response_time,
                "sections_processed": sections_processed,
                "data_extracted": data_extracted
            })
            
            # Update daily stats
            self.daily_stats["emails_processed"] += 1
            if success:
                self.daily_stats["successful_processing"] += 1
            else:
                self.daily_stats["failed_processing"] += 1
                if error_type:
                    if error_type not in self.system_logs["error_counts"]:
                        self.system_logs["error_counts"][error_type] = 0
                    self.system_logs["error_counts"][error_type] += 1
            
            self.daily_stats["total_response_time"] += response_time
    
    def log_system_uptime_check(self, is_available: bool):
        """Log system availability check"""
        self.system_logs["uptime_checks"].append({
            "timestamp": time.time(),
            "available": is_available
        })
    
    def log_system_performance(self, memory_mb: float, cpu_percent: float, active_connections: int):
        """Log system performance metrics"""
        self.system_logs["performance_metrics"] = {
            "memory_usage_mb": memory_mb,
            "cpu_usage_percent": cpu_percent,
            "active_connections": active_connections,
            "timestamp": time.time()
        }
    
    def evaluate_email_intelligence_performance(self) -> VCEmailIntelligenceMetrics:
        """Evaluate overall email intelligence performance"""
        
        # Calculate success rate
        total_emails = len(self.email_logs)
        successful_emails = sum(1 for log in self.email_logs.values() if log["success"])
        agent_success_rate = (successful_emails / total_emails * 100) if total_emails > 0 else 0
        
        # Calculate response times
        response_times = [log["response_time"] for log in self.email_logs.values() if log["response_time"] > 0]
        average_response_time = sum(response_times) / len(response_times) if response_times else 0
        fastest_response_time = min(response_times) if response_times else 0
        slowest_response_time = max(response_times) if response_times else 0
        
        # Calculate processing times
        processing_times = [log["processing_time"] for log in self.email_logs.values()]
        average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Calculate error rate
        total_errors = sum(1 for log in self.email_logs.values() if not log["success"])
        error_rate = (total_errors / total_emails * 100) if total_emails > 0 else 0
        
        # Calculate system uptime
        uptime_checks = self.system_logs["uptime_checks"]
        if uptime_checks:
            available_checks = sum(1 for check in uptime_checks if check["available"])
            system_uptime = (available_checks / len(uptime_checks) * 100) if uptime_checks else 100
        else:
            system_uptime = 100  # Assume 100% if no checks logged
        
        # Get system performance metrics
        performance = self.system_logs["performance_metrics"]
        memory_usage = performance.get("memory_usage_mb", 0) if performance else 0
        cpu_usage = performance.get("cpu_usage_percent", 0) if performance else 0
        active_connections = performance.get("active_connections", 0) if performance else 0
        
        # Calculate error types
        error_types = self.system_logs["error_counts"]
        network_errors = error_types.get("network", 0)
        parsing_errors = error_types.get("parsing", 0)
        api_errors = error_types.get("api", 0)
        
        return VCEmailIntelligenceMetrics(
            agent_success_rate=agent_success_rate,
            average_response_time=average_response_time,
            system_uptime=system_uptime,
            error_rate=error_rate,
            daily_email_volume=self.daily_stats["emails_processed"],
            weekly_email_volume=self.daily_stats["emails_processed"] * 7,  # Estimate
            total_emails_processed=total_emails,
            fastest_response_time=fastest_response_time,
            slowest_response_time=slowest_response_time,
            average_processing_time=average_processing_time,
            total_errors=total_errors,
            error_types=error_types,
            network_errors=network_errors,
            parsing_errors=parsing_errors,
            api_errors=api_errors,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            active_connections=active_connections,
            evaluation_timestamp=datetime.now().isoformat()
        )
    
    def generate_email_intelligence_report(self, metrics: VCEmailIntelligenceMetrics) -> str:
        """Generate comprehensive email intelligence evaluation report"""
        report = f"""
VC EMAIL INTELLIGENCE EVALUATION REPORT
======================================

SYSTEM PERFORMANCE
------------------
✅ Agent Success Rate: {metrics.agent_success_rate:.1f}%
⚡ Average Response Time: {metrics.average_response_time:.1f} seconds
🟢 System Uptime: {metrics.system_uptime:.1f}%
❌ Error Rate: {metrics.error_rate:.1f}%

VOLUME METRICS
--------------
📧 Daily Email Volume: {metrics.daily_email_volume}
📊 Weekly Email Volume: {metrics.weekly_email_volume}
📈 Total Emails Processed: {metrics.total_emails_processed}

PERFORMANCE METRICS
------------------
🚀 Fastest Response Time: {metrics.fastest_response_time:.1f} seconds
🐌 Slowest Response Time: {metrics.slowest_response_time:.1f} seconds
⏱️ Average Processing Time: {metrics.average_processing_time:.1f} seconds

ERROR ANALYSIS
--------------
🚫 Total Errors: {metrics.total_errors}
🌐 Network Errors: {metrics.network_errors}
🔧 Parsing Errors: {metrics.parsing_errors}
🔌 API Errors: {metrics.api_errors}

SYSTEM HEALTH
-------------
💾 Memory Usage: {metrics.memory_usage_mb:.1f} MB
🖥️ CPU Usage: {metrics.cpu_usage_percent:.1f}%
🔗 Active Connections: {metrics.active_connections}

ERROR TYPE BREAKDOWN
-------------------
"""
        
        for error_type, count in metrics.error_types.items():
            report += f"• {error_type.title()}: {count}\n"
        
        return report
    
    def save_metrics(self, metrics: VCEmailIntelligenceMetrics, output_dir: str):
        """Save email intelligence metrics to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = os.path.join(output_dir, f"vc_email_intelligence_metrics_{timestamp}.json")
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics.__dict__, f, indent=2, default=str)
        
        return metrics_file
    
    def get_performance_alerts(self, metrics: VCEmailIntelligenceMetrics) -> List[str]:
        """Get performance alerts based on metrics"""
        alerts = []
        
        if metrics.agent_success_rate < 90:
            alerts.append(f"⚠️ Agent success rate ({metrics.agent_success_rate:.1f}%) below target (90%)")
        
        if metrics.average_response_time > 60:
            alerts.append(f"⚠️ Average response time ({metrics.average_response_time:.1f}s) above target (60s)")
        
        if metrics.system_uptime < 95:
            alerts.append(f"⚠️ System uptime ({metrics.system_uptime:.1f}%) below target (95%)")
        
        if metrics.error_rate > 5:
            alerts.append(f"⚠️ Error rate ({metrics.error_rate:.1f}%) above target (5%)")
        
        if metrics.memory_usage_mb > 1000:
            alerts.append(f"⚠️ High memory usage ({metrics.memory_usage_mb:.1f}MB)")
        
        if metrics.cpu_usage_percent > 80:
            alerts.append(f"⚠️ High CPU usage ({metrics.cpu_usage_percent:.1f}%)")
        
        return alerts 