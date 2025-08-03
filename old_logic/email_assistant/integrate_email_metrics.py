"""
Integration script to add evaluation metrics to email assistant system
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import evaluation metrics
sys.path.append(str(Path(__file__).parent.parent))

from evaluation_metrics.core.vc_email_intelligence_metrics import VCEmailIntelligenceMetrics

class EmailMetricsIntegration:
    """Integrates evaluation metrics with existing email assistant system"""
    
    def __init__(self):
        self.metrics = VCEmailIntelligenceMetrics()
        self.current_email = None
        
    def start_email_processing(self, email_id: str, email_content: str = None):
        """Start tracking email processing"""
        self.current_email = {
            'email_id': email_id,
            'start_time': time.time(),
            'processing_steps': [],
            'success': False,
            'error_type': None,
            'response_time': 0,
            'sections_processed': 0,
            'data_extracted': False
        }
        print(f"[Email Metrics] Started processing email {email_id}")
        
    def log_processing_step(self, step_name: str, duration: float, success: bool, error: str = None):
        """Log a processing step"""
        if not self.current_email:
            return
            
        step_data = {
            'step': step_name,
            'duration': duration,
            'success': success,
            'error': error,
            'timestamp': time.time()
        }
        
        self.current_email['processing_steps'].append(step_data)
        
        if success:
            self.current_email['sections_processed'] += 1
        else:
            self.current_email['error_type'] = error
            
    def log_response_generation(self, response_time: float, success: bool):
        """Log response generation metrics"""
        if not self.current_email:
            return
            
        self.current_email['response_time'] = response_time
        self.current_email['success'] = success
        
    def log_data_extraction(self, data_found: bool):
        """Log data extraction success"""
        if not self.current_email:
            return
            
        self.current_email['data_extracted'] = data_found
        
    def end_email_processing(self):
        """End email processing and save metrics"""
        if not self.current_email:
            return
            
        total_time = time.time() - self.current_email['start_time']
        
        # Calculate metrics
        success_rate = 100 if self.current_email['success'] else 0
        avg_step_time = 0
        if self.current_email['processing_steps']:
            total_step_time = sum(step['duration'] for step in self.current_email['processing_steps'])
            avg_step_time = total_step_time / len(self.current_email['processing_steps'])
            
        # Create metrics object
        email_metrics = {
            'email_id': self.current_email['email_id'],
            'processing_time_seconds': total_time,
            'success': self.current_email['success'],
            'error_type': self.current_email['error_type'],
            'response_time_seconds': self.current_email['response_time'],
            'sections_processed': self.current_email['sections_processed'],
            'data_extracted': self.current_email['data_extracted'],
            'processing_steps': self.current_email['processing_steps']
        }
        
        # Save to metrics system
        self.metrics.add_email_metrics(email_metrics)
        
        # Print summary
        print(f"\n[Email Metrics] Processing Summary for {self.current_email['email_id']}:")
        print(f"  ✅ Success: {'Yes' if self.current_email['success'] else 'No'}")
        print(f"  ⏱️  Total Time: {total_time:.2f}s")
        print(f"  📊 Sections Processed: {self.current_email['sections_processed']}")
        print(f"  🔄 Response Time: {self.current_email['response_time']:.2f}s")
        print(f"  📋 Data Extracted: {'Yes' if self.current_email['data_extracted'] else 'No'}")
        if self.current_email['error_type']:
            print(f"  ❌ Error: {self.current_email['error_type']}")
        
        # Reset current email
        self.current_email = None
        
    def get_overall_metrics(self):
        """Get overall email processing metrics"""
        return self.metrics.get_overall_metrics()
        
    def save_metrics_report(self, output_dir: str = None):
        """Save detailed metrics report"""
        if output_dir is None:
            output_dir = Path(__file__).parent / "results"
            
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed metrics
        detailed_file = os.path.join(output_dir, f"email_metrics_{timestamp}.json")
        self.metrics.save_detailed_metrics(detailed_file)
        
        # Generate summary report
        summary_file = os.path.join(output_dir, f"email_summary_{timestamp}.txt")
        self.metrics.generate_summary_report(summary_file)
        
        print(f"\n[Email Metrics] Reports saved:")
        print(f"  📊 Detailed metrics: {detailed_file}")
        print(f"  📋 Summary report: {summary_file}")
        
        return detailed_file, summary_file


# Integration with existing API server
def integrate_with_api_server():
    """Integration function for api_server.py"""
    
    # Create metrics instance
    metrics = EmailMetricsIntegration()
    
    def tracked_analyze_question(question: str, email_id: str = None):
        """Tracked version of question analysis"""
        if not email_id:
            email_id = f"email_{int(time.time())}"
            
        metrics.start_email_processing(email_id)
        
        try:
            # Track question parsing
            start_time = time.time()
            # Simulate question parsing step
            time.sleep(0.1)  # Simulate processing
            metrics.log_processing_step("question_parsing", time.time() - start_time, True)
            
            # Track agent initialization
            start_time = time.time()
            # Simulate agent initialization
            time.sleep(0.2)  # Simulate processing
            metrics.log_processing_step("agent_initialization", time.time() - start_time, True)
            
            # Track analysis
            start_time = time.time()
            # Here you would call the actual analysis function
            # For now, simulate the analysis
            time.sleep(0.5)  # Simulate processing
            analysis_success = True  # This would be the actual result
            metrics.log_processing_step("analysis", time.time() - start_time, analysis_success)
            
            # Track response generation
            start_time = time.time()
            # Simulate response generation
            time.sleep(0.3)  # Simulate processing
            response_time = time.time() - start_time
            metrics.log_response_generation(response_time, True)
            
            # Track data extraction
            metrics.log_data_extraction(True)  # Assume data was extracted
            
            # Simulate result
            result = {
                'answer': 'This is a simulated response.',
                'sources': ['Simulated source 1', 'Simulated source 2'],
                'validation': 'success'
            }
            
            return result
            
        except Exception as e:
            metrics.log_processing_step("error_handling", 0, False, str(e))
            raise
        finally:
            metrics.end_email_processing()
    
    return metrics, tracked_analyze_question


# Integration with existing analyze_vc_questions.py
def integrate_with_analyze_questions():
    """Integration function for analyze_vc_questions.py"""
    
    metrics = EmailMetricsIntegration()
    
    def tracked_analyze_vc_questions(email_content: str, email_id: str = None):
        """Tracked version of VC question analysis"""
        if not email_id:
            email_id = f"vc_email_{int(time.time())}"
            
        metrics.start_email_processing(email_id, email_content)
        
        try:
            # Track email parsing
            start_time = time.time()
            # Simulate email parsing
            time.sleep(0.1)
            metrics.log_processing_step("email_parsing", time.time() - start_time, True)
            
            # Track question extraction
            start_time = time.time()
            # Simulate question extraction
            time.sleep(0.2)
            metrics.log_processing_step("question_extraction", time.time() - start_time, True)
            
            # Track VC analysis
            start_time = time.time()
            # Simulate VC analysis
            time.sleep(0.8)
            metrics.log_processing_step("vc_analysis", time.time() - start_time, True)
            
            # Track response generation
            start_time = time.time()
            # Simulate response generation
            time.sleep(0.4)
            response_time = time.time() - start_time
            metrics.log_response_generation(response_time, True)
            
            # Track data extraction
            metrics.log_data_extraction(True)
            
            # Simulate result
            result = {
                'questions': ['What is the market size?', 'Who are the competitors?'],
                'answers': ['Market size is $10B', 'Competitors include X, Y, Z'],
                'sources': ['Source 1', 'Source 2']
            }
            
            return result
            
        except Exception as e:
            metrics.log_processing_step("error_handling", 0, False, str(e))
            raise
        finally:
            metrics.end_email_processing()
    
    return metrics, tracked_analyze_vc_questions


if __name__ == "__main__":
    # Example usage
    metrics = EmailMetricsIntegration()
    
    # Simulate email processing
    metrics.start_email_processing("test_email_123", "Test email content")
    
    # Log processing steps
    metrics.log_processing_step("parsing", 0.1, True)
    metrics.log_processing_step("analysis", 0.5, True)
    metrics.log_processing_step("response", 0.3, True)
    
    # Log response generation
    metrics.log_response_generation(0.3, True)
    
    # Log data extraction
    metrics.log_data_extraction(True)
    
    # End processing
    metrics.end_email_processing()
    
    # Save reports
    metrics.save_metrics_report()
    
    # Show overall metrics
    overall = metrics.get_overall_metrics()
    print(f"\n[Overall] Success Rate: {overall['overall_success_rate']:.1f}%")
    print(f"[Overall] Avg Response Time: {overall['average_response_time']:.2f}s") 