"""
Steam Arena - Airflow DAG for Playtime Tracking

This DAG automates:
1. Daily snapshots of playtime data
2. Monthly calculation of yearly stats
3. Data retention and cleanup

Schedule:
- Snapshots: Daily at midnight
- Yearly stats: Monthly on the 1st (for previous month data)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
import os
import requests
import logging

logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://backend:8000')
API_BASE = f"{BACKEND_URL}/api/v1"

# Default args for the DAG
default_args = {
    'owner': 'steam_arena',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}


def create_playtime_snapshot(**context):
    """
    Create a snapshot of current playtime for all users.
    This captures the state at this moment in time.
    """
    try:
        logger.info("Creating playtime snapshot...")
        
        response = requests.post(
            f"{API_BASE}/playtime-tracking/snapshot",
            timeout=300  # 5 minutes timeout
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Snapshot created successfully: {result['snapshots_created']} records")
        
        # Push to XCom for monitoring
        context['task_instance'].xcom_push(
            key='snapshot_count',
            value=result['snapshots_created']
        )
        context['task_instance'].xcom_push(
            key='snapshot_timestamp',
            value=result['timestamp']
        )
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create snapshot: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during snapshot creation: {str(e)}")
        raise


def calculate_yearly_stats(**context):
    """
    Calculate yearly statistics for the current year.
    This should be run monthly to keep stats up to date.
    """
    try:
        current_year = datetime.now().year
        logger.info(f"Calculating yearly stats for {current_year}...")
        
        response = requests.post(
            f"{API_BASE}/playtime-tracking/calculate-yearly-stats/{current_year}",
            timeout=600  # 10 minutes timeout
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Stats calculated for {result['users_processed']} users")
        
        # Push to XCom
        context['task_instance'].xcom_push(
            key='users_processed',
            value=result['users_processed']
        )
        context['task_instance'].xcom_push(
            key='year',
            value=result['year']
        )
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to calculate stats: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during stats calculation: {str(e)}")
        raise


def verify_snapshot_health(**context):
    """
    Verify that snapshots are being created regularly.
    Check the snapshot history and alert if gaps detected.
    """
    try:
        logger.info("Verifying snapshot health...")
        
        response = requests.get(
            f"{API_BASE}/playtime-tracking/snapshot-history",
            params={'limit': 7},  # Check last 7 days
            timeout=30
        )
        response.raise_for_status()
        
        history = response.json()
        
        if len(history) < 7:
            logger.warning(f"Only {len(history)} snapshots found in last 7 days")
        else:
            logger.info(f"✓ Snapshot history healthy: {len(history)} snapshots in last 7 days")
        
        # Check for gaps
        dates = [datetime.fromisoformat(h['date']) for h in history]
        if dates:
            dates.sort()
            gaps = []
            for i in range(len(dates) - 1):
                diff = (dates[i+1] - dates[i]).days
                if diff > 1:
                    gaps.append(f"{dates[i].date()} to {dates[i+1].date()} ({diff} days)")
            
            if gaps:
                logger.warning(f"⚠️  Gaps detected in snapshot history: {', '.join(gaps)}")
            else:
                logger.info("✓ No gaps detected in snapshot history")
        
        context['task_instance'].xcom_push(
            key='snapshot_count_week',
            value=len(history)
        )
        
        return {'healthy': len(history) >= 6, 'count': len(history)}
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # Don't fail the DAG if health check fails
        return {'healthy': False, 'error': str(e)}


def send_notification(**context):
    """
    Send notification about snapshot completion.
    Can be extended to send email, Slack, etc.
    """
    snapshot_count = context['task_instance'].xcom_pull(
        task_ids='create_snapshot',
        key='snapshot_count'
    )
    
    logger.info(f"📊 Daily snapshot completed: {snapshot_count} records created")
    
    # TODO: Add Slack/Email notification here if needed
    return f"Snapshot notification sent: {snapshot_count} records"


# ============================================================================
# DAG 1: Daily Playtime Snapshot
# ============================================================================

daily_snapshot_dag = DAG(
    'steam_arena_daily_playtime_snapshot',
    default_args=default_args,
    description='Create daily snapshot of playtime data for all users',
    schedule_interval='0 0 * * *',  # Every day at midnight
    start_date=datetime(2025, 12, 14),
    catchup=False,  # Don't backfill - only run for current day
    tags=['steam-arena', 'playtime', 'tracking', 'daily'],
    max_active_runs=1,
)

with daily_snapshot_dag:
    # Task 1: Create the snapshot
    snapshot_task = PythonOperator(
        task_id='create_snapshot',
        python_callable=create_playtime_snapshot,
        doc_md="""
        ## Create Playtime Snapshot
        
        Creates a snapshot of current playtime for all users and games.
        This captures the state at this moment in time for historical tracking.
        
        **API Endpoint:** `POST /api/v1/playtime-tracking/snapshot`
        
        **Returns:** Number of snapshots created
        """
    )
    
    # Task 2: Verify snapshot health
    health_check_task = PythonOperator(
        task_id='verify_health',
        python_callable=verify_snapshot_health,
        doc_md="""
        ## Verify Snapshot Health
        
        Checks the snapshot history to ensure snapshots are being created regularly.
        Detects gaps and alerts if issues found.
        
        **API Endpoint:** `GET /api/v1/playtime-tracking/snapshot-history`
        """
    )
    
    # Task 3: Send notification
    notification_task = PythonOperator(
        task_id='send_notification',
        python_callable=send_notification,
        doc_md="""
        ## Send Notification
        
        Sends a notification about the snapshot completion.
        Can be extended to send email, Slack, etc.
        """
    )
    
    # Define task dependencies
    snapshot_task >> health_check_task >> notification_task


# ============================================================================
# DAG 2: Monthly Yearly Stats Calculation
# ============================================================================

monthly_stats_dag = DAG(
    'steam_arena_monthly_yearly_stats',
    default_args=default_args,
    description='Calculate yearly statistics from snapshots (monthly)',
    schedule_interval='0 2 1 * *',  # 1st of each month at 2 AM
    start_date=datetime(2025, 12, 1),
    catchup=False,
    tags=['steam-arena', 'playtime', 'stats', 'monthly'],
    max_active_runs=1,
)

with monthly_stats_dag:
    # Task 1: Calculate current year stats
    calculate_current_year = PythonOperator(
        task_id='calculate_current_year_stats',
        python_callable=calculate_yearly_stats,
        doc_md="""
        ## Calculate Current Year Stats
        
        Calculates yearly statistics for the current year based on snapshots.
        Compares snapshots from start/end of year to determine playtime.
        
        **API Endpoint:** `POST /api/v1/playtime-tracking/calculate-yearly-stats/{year}`
        """
    )
    
    # Task 2: Health check after calculation
    health_check_stats = PythonOperator(
        task_id='verify_health_after_stats',
        python_callable=verify_snapshot_health,
    )
    
    calculate_current_year >> health_check_stats


# ============================================================================
# DAG 3: End of Year Stats (Manual/Scheduled)
# ============================================================================

end_of_year_dag = DAG(
    'steam_arena_end_of_year_stats',
    default_args=default_args,
    description='Calculate final yearly statistics at end of year',
    schedule_interval='0 3 31 12 *',  # December 31st at 3 AM
    start_date=datetime(2025, 12, 31),
    catchup=False,
    tags=['steam-arena', 'playtime', 'stats', 'yearly'],
)

with end_of_year_dag:
    def calculate_previous_year(**context):
        """Calculate stats for the year that just ended."""
        previous_year = datetime.now().year - 1
        logger.info(f"🎊 Calculating final stats for year {previous_year}...")
        
        response = requests.post(
            f"{API_BASE}/playtime-tracking/calculate-yearly-stats/{previous_year}",
            timeout=600
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✓ Final stats for {previous_year}: {result['users_processed']} users")
        
        return result
    
    final_stats = PythonOperator(
        task_id='calculate_final_yearly_stats',
        python_callable=calculate_previous_year,
        doc_md="""
        ## Calculate Final Yearly Stats
        
        Runs on December 31st to calculate final statistics for the year that just ended.
        This ensures accurate year-end reporting.
        """
    )


# ============================================================================
# DAG 4: Manual Snapshot (On-Demand)
# ============================================================================

manual_snapshot_dag = DAG(
    'steam_arena_manual_playtime_snapshot',
    default_args=default_args,
    description='Manual snapshot creation (trigger on-demand)',
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2025, 12, 14),
    catchup=False,
    tags=['steam-arena', 'playtime', 'manual'],
)

with manual_snapshot_dag:
    manual_snapshot = PythonOperator(
        task_id='create_manual_snapshot',
        python_callable=create_playtime_snapshot,
        doc_md="""
        ## Manual Snapshot
        
        Trigger this DAG manually from Airflow UI to create a snapshot on-demand.
        Useful for testing or creating extra snapshots.
        """
    )


# ============================================================================
# DAG 5: Cleanup Old Snapshots (Monthly)
# ============================================================================

cleanup_dag = DAG(
    'steam_arena_cleanup_old_snapshots',
    default_args=default_args,
    description='Cleanup snapshots older than retention period',
    schedule_interval='0 4 1 * *',  # 1st of each month at 4 AM
    start_date=datetime(2025, 12, 1),
    catchup=False,
    tags=['steam-arena', 'playtime', 'cleanup', 'maintenance'],
)

with cleanup_dag:
    def cleanup_old_snapshots(**context):
        """
        Cleanup snapshots older than retention period.
        Keep daily snapshots for 1 year, then only monthly snapshots.
        """
        import psycopg2
        from datetime import datetime, timedelta
        
        # This would require database access
        # For now, just log the intent
        logger.info("🧹 Cleanup task - would delete snapshots older than 365 days")
        logger.info("TODO: Implement database cleanup logic")
        
        # Example logic (to be implemented):
        # - Keep all snapshots from last 365 days
        # - Keep only 1st of month snapshots older than 365 days
        # - Delete the rest
        
        return "Cleanup completed (placeholder)"
    
    cleanup_task = PythonOperator(
        task_id='cleanup_old_snapshots',
        python_callable=cleanup_old_snapshots,
        doc_md="""
        ## Cleanup Old Snapshots
        
        Removes old snapshot data to manage database size.
        
        **Retention Policy:**
        - Last 365 days: Keep all snapshots
        - Older than 365 days: Keep only 1st of month
        """
    )
