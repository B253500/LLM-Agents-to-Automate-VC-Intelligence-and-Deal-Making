"""
Modified download_reports.py with automatic metrics recording
Run this script and it will automatically generate metrics reports
"""

import sys
import os
import time
from pathlib import Path
import platform
import os

# Add the parent directory (for metrics) and scripts dir (for site-specific scrapers)
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent / "scripts"))

from integrate_scraping_metrics import ScrapingMetricsIntegration
from playwright_stealth import Stealth

# Import all the original functions from download_reports.py
from download_reports import (
    scrape_and_download_crunchbase,
    scrape_and_download_pitchbook,
    scrape_and_download_techcrunch,
    # New: simple Crunchbase News scraper, defined below
    # scrape_and_download_crunchbase_news,
    sync_playwright,
    PlaywrightError,
    NAV_TIMEOUT
)
# Use the standalone Beauhurst implementation to match behavior
from download_beauhurst import scrape_and_download_beauhurst

def main_with_metrics():
    """Main function with automatic metrics recording"""
    
    # Initialize metrics
    metrics = ScrapingMetricsIntegration()
    
    print("🚀 Starting web scraping with metrics tracking...")
    
    with sync_playwright() as pw:
        # Prefer system Chrome on macOS; allow HEADLESS=1 to hide browser
        headless = os.getenv("HEADLESS", "0") == "1"
        try:
            if platform.system() == "Darwin":
                browser = pw.chromium.launch(channel="chrome", headless=headless)
            else:
                browser = pw.chromium.launch(headless=True if headless else False)
        except Exception:
            # Fallback to default bundled Chromium
            browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=True)
        # Align environment with stable standalone runs
        try:
            context.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            })
        except Exception:
            pass
        try:
            stealth = Stealth()
            stealth.apply_stealth_sync(context)
        except Exception:
            pass
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)

        # Ensure Beauhurst (scripts/* using core.download_utils) saves into web_scraping paths
        try:
            import core.download_utils as core_du  # type: ignore
            from datetime import datetime
            today_str = datetime.now().strftime('%Y-%m-%d')
            core_du.DOWNLOAD_DIR = Path(__file__).parent / "data" / "vc_reports" / today_str
            core_du.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            core_du.MAPPING_FILE = Path(__file__).parent / "downloaded_reports.json"
        except Exception:
            pass

        # Inject metrics into download_reports so per-download events are counted
        try:
            from download_reports import set_metrics as _set_metrics
            _set_metrics(metrics)
        except Exception:
            pass

        # Utility: read mapping count
        def _mapping_count():
            try:
                from json import load
                p = Path(__file__).parent / "downloaded_reports.json"
                if p.exists():
                    with open(p, 'r') as f:
                        data = load(f)
                        return len(data) if isinstance(data, dict) else 0
            except Exception:
                pass
            return 0

        # Utility: compute Saved split by source and type
        def _saved_split():
            import json, re
            p = Path(__file__).parent / "downloaded_reports.json"
            split = {
                'TechCrunch': {'DirectSaved': 0, 'FallbackSaved': 0, 'EmailSent': 0},
                'Beauhurst': {'DirectSaved': 0, 'FallbackSaved': 0, 'EmailSent': 0},
                'PitchBook': {'DirectSaved': 0, 'FallbackSaved': 0, 'EmailSent': 0},
                'Crunchbase': {'DirectSaved': 0, 'FallbackSaved': 0, 'EmailSent': 0},
            }
            if not p.exists():
                return split
            try:
                data = json.loads(p.read_text())
                for url, fname in (data.items() if isinstance(data, dict) else []):
                    src = None
                    u = (url or '').lower()
                    if 'techcrunch.com' in u:
                        src = 'TechCrunch'
                    elif 'beauhurst.com' in u:
                        src = 'Beauhurst'
                    elif 'pitchbook.com' in u:
                        src = 'PitchBook'
                    elif 'crunchbase.com' in u or 'about.crunchbase.com' in u or 'news.crunchbase.com' in u:
                        src = 'Crunchbase'
                    if not src:
                        continue
                    if fname == 'email_sent':
                        split[src]['EmailSent'] += 1
                    elif isinstance(fname, str) and fname.lower().endswith('.pdf'):
                        # Heuristic: if filename looks like a clean server-provided PDF name (not a page title capture)
                        # treat as DirectSaved; otherwise page-PDF fallback
                        if re.match(r"^[\w.-]+\.pdf$", fname):
                            split[src]['DirectSaved'] += 1
                        else:
                            split[src]['FallbackSaved'] += 1
                    else:
                        split[src]['FallbackSaved'] += 1
            except Exception:
                pass
            return split

        # Helper: allow skipping and checkpoint saving after each source
        def _skip(name: str) -> bool:
            return os.getenv(f"SKIP_{name.upper()}", "0") == "1"

        def _checkpoint():
            try:
                metrics.save_metrics_report()
            except Exception:
                pass

        # Track Crunchbase scraping (cap 100)
        print("\n📊 Starting Crunchbase scraping with metrics (cap 100)...")
        if _skip("Crunchbase"):
            print("⏭️  Skipping Crunchbase (SKIP_CRUNCHBASE=1)")
        else:
            metrics.start_scraping_session("Crunchbase")
            try:
                before = _mapping_count()
                scrape_and_download_crunchbase(page, max_attempts=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][Crunchbase]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.8)
                print("✅ Crunchbase scraping completed successfully")
            except Exception as e:
                print(f"❌ Crunchbase scraping failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                # Print Saved split snapshot after this source
                ss = _saved_split()
                print("[Saved Split][Crunchbase]", ss.get('Crunchbase', {}))

        # Track Crunchbase News (cap 100)
        print("\n📊 Starting Crunchbase News with metrics (cap 100)...")
        if _skip("CrunchbaseNews"):
            print("⏭️  Skipping Crunchbase News (SKIP_CRUNCHBASENEWS=1)")
        else:
            metrics.start_scraping_session("CrunchbaseNews")
            try:
                from download_reports import scrape_and_download_crunchbase_news
                before = _mapping_count()
                scrape_and_download_crunchbase_news(page, max_attempts=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][CrunchbaseNews]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.75)
                print("✅ Crunchbase News completed successfully")
            except Exception as e:
                print(f"❌ Crunchbase News failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][Crunchbase]", ss.get('Crunchbase', {}))

        # Track Beauhurst scraping (cap 100)
        print("\n📊 Starting Beauhurst scraping with metrics (cap 100)...")
        if _skip("Beauhurst"):
            print("⏭️  Skipping Beauhurst (SKIP_BEAUHURST=1)")
        else:
            metrics.start_scraping_session("Beauhurst")
            try:
                # Pass metrics into standalone Beauhurst so its counters reflect activity
                try:
                    from download_beauhurst import set_metrics as _bh_set_metrics
                    _bh_set_metrics(metrics)
                except Exception:
                    pass
                before = _mapping_count()
                scrape_and_download_beauhurst(page, max_pages=20)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][Beauhurst]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.9)
                print("✅ Beauhurst scraping completed successfully")
            except Exception as e:
                print(f"❌ Beauhurst scraping failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][Beauhurst]", ss.get('Beauhurst', {}))

        # Track TechCrunch scraping (cap ~100 via clicks) — moved earlier per requested order
        print("\n📊 Starting TechCrunch scraping with metrics (cap ~100)...")
        if _skip("TechCrunch"):
            print("⏭️  Skipping TechCrunch (SKIP_TECHCRUNCH=1)")
        else:
            metrics.start_scraping_session("TechCrunch")
            try:
                before = _mapping_count()
                scrape_and_download_techcrunch(page, max_clicks=100, max_saved=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][TechCrunch]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.7)
                print("✅ TechCrunch scraping completed successfully")
            except Exception as e:
                print(f"❌ TechCrunch scraping failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][TechCrunch]", ss.get('TechCrunch', {}))

        # Track PitchBook scraping (cap 100)
        print("\n📊 Starting PitchBook scraping with metrics (cap 100)...")
        if _skip("PitchBook"):
            print("⏭️  Skipping PitchBook (SKIP_PITCHBOOK=1)")
        else:
            metrics.start_scraping_session("PitchBook")
            try:
                before = _mapping_count()
                scrape_and_download_pitchbook(page, max_attempts=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][PitchBook]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.85)
                print("✅ PitchBook scraping completed successfully")
            except Exception as e:
                print(f"❌ PitchBook scraping failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][PitchBook]", ss.get('PitchBook', {}))

        # Track PitchBook News categories (cap 100)
        print("\n📊 Starting PitchBook News categories with metrics (cap 100)...")
        if _skip("PitchBookNews"):
            print("⏭️  Skipping PitchBook News (SKIP_PITCHBOOKNEWS=1)")
        else:
            metrics.start_scraping_session("PitchBookNews")
            try:
                from download_reports import scrape_and_download_pitchbook_news
                before = _mapping_count()
                scrape_and_download_pitchbook_news(page, max_attempts=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][PitchBookNews]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.7)
                print("✅ PitchBook News completed successfully")
            except Exception as e:
                print(f"❌ PitchBook News failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][PitchBook]", ss.get('PitchBook', {}))

        # Track PitchBook News Search (cap 100)
        print("\n📊 Starting PitchBook News Search with metrics (cap 100)...")
        if _skip("PitchBookNewsSearch"):
            print("⏭️  Skipping PitchBook News Search (SKIP_PITCHBOOKNEWSSEARCH=1)")
        else:
            metrics.start_scraping_session("PitchBookNewsSearch")
            try:
                from download_reports import scrape_and_download_pitchbook_news_search
                before = _mapping_count()
                scrape_and_download_pitchbook_news_search(page, max_attempts=100)
                after = _mapping_count()
                actual_new = max(after - before, 0)
                print(f"[Actual Downloads][PitchBookNewsSearch]: {actual_new}")
                metrics.log_data_extraction(data_quality_score=0.7)
                print("✅ PitchBook News Search completed successfully")
            except Exception as e:
                print(f"❌ PitchBook News Search failed: {e}")
                metrics.log_request(False, error_type=str(e))
            finally:
                metrics.end_scraping_session()
                _checkpoint()
                ss = _saved_split()
                print("[Saved Split][PitchBook]", ss.get('PitchBook', {}))

        

        browser.close()

    # Generate and save metrics reports
    print("\n📈 Generating metrics reports...")
    detailed_file, summary_file = metrics.save_metrics_report()
    
    # Show overall metrics
    overall = metrics.get_overall_metrics()
    print(f"\n🎯 OVERALL SCRAPING METRICS:")
    print(f"  ✅ Success Rate: {overall['overall_success_rate']:.1f}%")
    print(f"  ⏱️  Avg Response Time: {overall['average_response_time']:.2f}s")
    print(f"  📊 Total Requests: {overall['total_requests']}")
    print(f"  ❌ Failed Requests: {overall['total_failed_requests']}")
    print(f"  🔄 Rate Limit Hits: {overall['total_rate_limit_hits']}")
    print(f"  📋 Data Quality Score: {overall['average_data_quality']:.2f}/1.0")
    
    print(f"\n📊 Reports saved:")
    print(f"  📈 Detailed metrics: {detailed_file}")
    print(f"  📋 Summary report: {summary_file}")
    
    return metrics

if __name__ == '__main__':
    main_with_metrics() 