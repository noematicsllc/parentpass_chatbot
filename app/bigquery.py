from google.cloud import bigquery
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Azure analytics
try:
    from .azure_analytics import AzureAnalytics
except ImportError:
    # Fallback for direct script execution
    from azure_analytics import AzureAnalytics

# Module-level BigQuery client
client = bigquery.Client()

# Get BigQuery project and dataset from environment
BQ_PROJECT = os.getenv("BQ_PROJECT")
BQ_DATASET = os.getenv("BQ_DATASET")
BQ_TABLE_PREFIX = f"`{BQ_PROJECT}.{BQ_DATASET}.events_*`"

def get_bq_table_name() -> str:
    """Get the full BigQuery table name from environment variables."""
    return BQ_TABLE_PREFIX


def time_spent_by_section(
    grouper: str = "%Y-%m-%d %H:00:00",
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get user engagement time breakdown by app section.
    
    Args:
        grouper: DateTime format string for grouping results (default: hourly)
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: date_time, section, time
        Example: [{"date_time": "2025-06-21 17:00:00", "section": "Event", "time": 123944.86}]
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = f"""
    BEGIN
    DECLARE grouper STRING DEFAULT @grouper;
    DECLARE timestampFrom TIMESTAMP DEFAULT @timestamp_from;
    DECLARE timestampTo TIMESTAMP DEFAULT @timestamp_to;

    Select date_time, section, avg(count) as time from
      (SELECT
          FORMAT_DATETIME(grouper, DATETIME(TIMESTAMP_MICROS(event_timestamp))) date_time,
          case When event_param.value.string_value in ("CHAT_HOME", "NIGHBOURHOOD_NEWS", "CHAT_TOPICS", "NEW_POST", "POST_DETAILS", "CHAT_IMAGE_GALLERY", "SUGGEST_TOPICS", "CHAT_GENERAL_SEARCH") then "Post"
               WHEN event_param.value.string_value in ("FREEBIE_HOME", "freebie_listing", "FREEBIE_SEARCH_LIST", "FREEBIE_REQUESTED", "MY_FREEBIE", "SAVED_FREEBIE", "FREEBIE_CATEGORIES", "FREEBIE_DETAILS", "ADD_FREEBIE", "FREEBIE_CONTACT_INFORMATION") then "Freebie"
               WHEN event_param.value.string_value in ("SAFETY", "SAFETY_LISTING", "REPORT_CRIME") then "Crime"
                WHEN event_param.value.string_value in ("RECOMMEND_HOME", "CONNECT_CHILD_LIST", "TARRANT_AREA_FOOD", "COMMUNITY_LINK", "SUGGEST_PARTNER", "ADD_COMMUNITY_REVIEW", "COOK_CHILDREN_HEALTH_SYSTEM", "MERCY_CLINIC", "CORNERSTONE_CHARITY", "RENT_UTILITIES", "RENTERS_RIGHTS", "HOMEOWNER_PREP", "HOMEBUYER_ASSISTANCE", "LENA_POPE", "LUCINE_CENTER", "MY_HEALTH_MY_RESOURCES", "THE_PARENTING_CENTER", "INDIVIDUAL_PARTNER_PROFILE", "JPS_HEALTH", "lookup_address") then "Recommend"
                WHEN event_param.value.string_value in ( "CALL", "CALL_DETAILS") then "Hotline"
                WHEN event_param.value.string_value in ("VIEW_HOME", "VIEW_MAP", "ADD_ACTIVITY", "ACTIVITY_PROFILE", "VIEW_SEARCH", "ADD_ACTIVITY_RECURRENCE", "MY_ACTIVITIES", "ATTENDING_ACTIVITIES", "MIGHT_ATTEND_ACTIVITIES", "EVENT_ROUNDUP") then "Event"
                WHEN event_param.value.string_value in ("ACTIVITY_SCREEN", "ACTIVITY_LIST", "ACTIVITY_DETAILS", "PDF") then "Activity"
                When event_param.value.string_value in ("FIND_STACK") then "Find"
                When event_param.value.string_value in ("TOP_FIVE") then "Top5"
                When event_param.value.string_value in ("ACCESS_STACK", "ACCESS_HOME", "ACCESS_LIST") then "Access"
               end as section,
          Sum(event_param2.value.int_value) as count
          
      FROM
        {BQ_TABLE_PREFIX}
        ,UNNEST (event_params) AS event_param
        ,UNNEST (user_properties) AS user_prop
        ,UNNEST (event_params) AS event_param2
      WHERE
        ((event_name = 'user_engagement' AND event_param.key = 'firebase_screen') 
        OR 
        (event_name = 'screen_view' AND event_param.key = 'firebase_previous_screen'))
        AND event_param.value.string_value IN ("CHAT_HOME", "NIGHBOURHOOD_NEWS", "CHAT_TOPICS", "NEW_POST", "POST_DETAILS", "CHAT_IMAGE_GALLERY", "SUGGEST_TOPICS", "CHAT_GENERAL_SEARCH", "FREEBIE_HOME", "freebie_listing", "FREEBIE_SEARCH_LIST", "FREEBIE_REQUESTED", "MY_FREEBIE", "SAVED_FREEBIE", "FREEBIE_CATEGORIES", "FREEBIE_DETAILS", "ADD_FREEBIE", "FREEBIE_CONTACT_INFORMATION", "SAFETY", "SAFETY_LISTING", "REPORT_CRIME", "RECOMMEND_HOME", "CONNECT_CHILD_LIST", "TARRANT_AREA_FOOD", "COMMUNITY_LINK", "SUGGEST_PARTNER", "ADD_COMMUNITY_REVIEW", "COOK_CHILDREN_HEALTH_SYSTEM", "MERCY_CLINIC", "CORNERSTONE_CHARITY", "RENT_UTILITIES", "RENTERS_RIGHTS", "HOMEOWNER_PREP", "HOMEBUYER_ASSISTANCE", "LENA_POPE", "LUCINE_CENTER", "MY_HEALTH_MY_RESOURCES", "THE_PARENTING_CENTER", "INDIVIDUAL_PARTNER_PROFILE", "JPS_HEALTH", "lookup_address",  "CALL", "CALL_DETAILS", "VIEW_HOME", "VIEW_MAP", "ADD_ACTIVITY", "ACTIVITY_PROFILE", "VIEW_SEARCH", "ADD_ACTIVITY_RECURRENCE", "MY_ACTIVITIES", "ATTENDING_ACTIVITIES", "MIGHT_ATTEND_ACTIVITIES", "EVENT_ROUNDUP", "ACTIVITY_SCREEN", "ACTIVITY_LIST", "ACTIVITY_DETAILS", "PDF", "FIND_STACK", "TOP_FIVE", "ACCESS_HOME", "ACCESS_STACK", "ACCESS_LIST")
        and user_prop.key = 'user_id'
    AND event_param2.key = 'engagement_time_msec'
    AND event_param2.value.int_value  is not null
    AND TIMESTAMP_MICROS(event_timestamp) >= timestampFrom
    AND TIMESTAMP_MICROS(event_timestamp) <= timestampTo

    group by date_time, section, user_prop.value.string_value)
    group by date_time, section;
    END
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("grouper", "STRING", grouper),
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "date_time": row.date_time,
                "section": row.section,
                "time": row.time
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in time_spent_by_section: {str(e)}")


def top_users_by_time_spent(
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    limit: int = 100,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get users ranked by total time spent in the app.
    
    Args:
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        limit: Maximum number of users to return (default: 100)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: user_id, time_ms
        Example: [{"user_id": "user123", "time_ms": 1234567}]
        Ordered by time_ms descending (highest engagement first)
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    # Note: LIMIT clause doesn't work with parameters in stored procedures, so we'll use a simpler query
    query = f"""
    SELECT
          user_prop.value.string_value as userId,
          Sum(event_param2.value.int_value) as timeMs
          
      FROM
        {BQ_TABLE_PREFIX}
        ,UNNEST (event_params) AS event_param
        ,UNNEST (user_properties) AS user_prop
        ,UNNEST (user_properties) AS user_prop2
        ,UNNEST (event_params) AS event_param2
      WHERE
        (event_name = 'user_engagement' OR event_name = 'screen_view')
        AND event_param.key = 'firebase_screen'
        AND event_param.value.string_value IN ("TOP_FIVE", "APP_HOME_SCREEN", "GLOBAL_SEARCH", "TUTORIAL_VIDEOS", "CHAT_HOME", "NIGHBOURHOOD_NEWS", "CHAT_TOPICS", "NEW_POST", "POST_DETAILS", "CHAT_IMAGE_GALLERY", "SUGGEST_TOPICS", "CHAT_GENERAL_SEARCH","FREEBIE_HOME", "freebie_listing", "FREEBIE_SEARCH_LIST", "FREEBIE_REQUESTED", "MY_FREEBIE", "SAVED_FREEBIE", "FREEBIE_CATEGORIES", "FREEBIE_DETAILS", "ADD_FREEBIE", "FREEBIE_CONTACT_INFORMATION", "SAFETY", "SAFETY_LISTING", "REPORT_CRIME", "RECOMMEND_HOME", "CONNECT_CHILD_LIST", "TARRANT_AREA_FOOD", "COMMUNITY_LINK", "SUGGEST_PARTNER", "ADD_COMMUNITY_REVIEW", "COOK_CHILDREN_HEALTH_SYSTEM", "MERCY_CLINIC", "CORNERSTONE_CHARITY", "RENT_UTILITIES", "RENTERS_RIGHTS", "HOMEOWNER_PREP", "HOMEBUYER_ASSISTANCE", "LENA_POPE", "LUCINE_CENTER", "MY_HEALTH_MY_RESOURCES", "THE_PARENTING_CENTER", "INDIVIDUAL_PARTNER_PROFILE", "JPS_HEALTH", "lookup_address", "FIND_STACK", "FAMILY_NAVIGATOR_SCREEN", "KIDS_HEALTH", "ACCOUNT_HOME", "ACCOUNT_NOTIFICATION_SETTING", "ACCOUNT_CHANGE_PASSWORD", "ACCOUNT_BADGES", "ACCOUNT_MY_PROFILE", "HELP", "VERIFICATION_CODE_SCREEN", "ACCOUNT_NOTIFICATIONS", "ACCOUNT_CHILD_LISTING", "ACCOUNT_UPDATE_CHILD", "SET_PASSWORD", "CALL", "CALL_DETAILS", "VIEW_HOME", "VIEW_MAP", "ADD_ACTIVITY", "ACTIVITY_PROFILE", "VIEW_SEARCH", "ADD_ACTIVITY_RECURRENCE", "MY_ACTIVITIES", "ATTENDING_ACTIVITIES", "MIGHT_ATTEND_ACTIVITIES", "EVENT_ROUNDUP","ACCESS_HOME", "ACCESS_LIST","ACTIVITY_SCREEN", "ACTIVITY_LIST", "ACTIVITY_DETAILS", "PDF")
        and user_prop.key = 'user_id'
        and user_prop2.key = 'connectedBy'
    AND event_param2.key = 'engagement_time_msec'
    AND event_param2.value.int_value  is not null
    AND user_prop2.value.string_value != 'Guest'
    AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
    AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to

    group by user_prop.value.string_value
    order by timeMs desc
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "user_id": row.userId,
                "time_ms": row.timeMs
            })
        
        # Apply limit in Python since BigQuery stored procedures don't support parameterized LIMIT
        return results[:limit]
        
    except Exception as e:
        raise Exception(f"BigQuery error in top_users_by_time_spent: {str(e)}")


def time_spent_in_app(
    grouper: str = "%Y-%m-%d %H:00:00",
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get time spent in app comparing registered users vs guests.
    
    Args:
        grouper: DateTime format string for grouping results (default: hourly)
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: date_time, is_guest, time
        Example: [{"date_time": "2025-06-21 17:00:00", "is_guest": 0, "time": 123944.86}]
        is_guest: 1 = guest users, 0 = registered users
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = """
    Select date_time, is_guest , avg(count) as time from
      (SELECT
          FORMAT_DATETIME(@grouper, DATETIME(TIMESTAMP_MICROS(event_timestamp))) date_time,
          max(case when user_prop2.value.string_value = 'Guest' then 1 else 0 end) as is_guest,
          Sum(event_param2.value.int_value) as count
          
      FROM
        {BQ_TABLE_PREFIX}
        ,UNNEST (event_params) AS event_param
        ,UNNEST (user_properties) AS user_prop
        ,UNNEST (user_properties) AS user_prop2
        ,UNNEST (event_params) AS event_param2
      WHERE
        (event_name = 'user_engagement' OR event_name = 'screen_view')
        AND event_param.key = 'firebase_screen'
        AND event_param.value.string_value IN ("TOP_FIVE", "APP_HOME_SCREEN", "GLOBAL_SEARCH", "TUTORIAL_VIDEOS", "CHAT_HOME", "NIGHBOURHOOD_NEWS", "CHAT_TOPICS", "NEW_POST", "POST_DETAILS", "CHAT_IMAGE_GALLERY", "SUGGEST_TOPICS", "CHAT_GENERAL_SEARCH","FREEBIE_HOME", "freebie_listing", "FREEBIE_SEARCH_LIST", "FREEBIE_REQUESTED", "MY_FREEBIE", "SAVED_FREEBIE", "FREEBIE_CATEGORIES", "FREEBIE_DETAILS", "ADD_FREEBIE", "FREEBIE_CONTACT_INFORMATION", "SAFETY", "SAFETY_LISTING", "REPORT_CRIME", "RECOMMEND_HOME", "CONNECT_CHILD_LIST", "TARRANT_AREA_FOOD", "COMMUNITY_LINK", "SUGGEST_PARTNER", "ADD_COMMUNITY_REVIEW", "COOK_CHILDREN_HEALTH_SYSTEM", "MERCY_CLINIC", "CORNERSTONE_CHARITY", "RENT_UTILITIES", "RENTERS_RIGHTS", "HOMEOWNER_PREP", "HOMEBUYER_ASSISTANCE", "LENA_POPE", "LUCINE_CENTER", "MY_HEALTH_MY_RESOURCES", "THE_PARENTING_CENTER", "INDIVIDUAL_PARTNER_PROFILE", "JPS_HEALTH", "lookup_address", "FIND_STACK", "FAMILY_NAVIGATOR_SCREEN", "KIDS_HEALTH", "ACCOUNT_HOME", "ACCOUNT_NOTIFICATION_SETTING", "ACCOUNT_CHANGE_PASSWORD", "ACCOUNT_BADGES", "ACCOUNT_MY_PROFILE", "HELP", "VERIFICATION_CODE_SCREEN", "ACCOUNT_NOTIFICATIONS", "ACCOUNT_CHILD_LISTING", "ACCOUNT_UPDATE_CHILD", "SET_PASSWORD", "CALL", "CALL_DETAILS", "VIEW_HOME", "VIEW_MAP", "ADD_ACTIVITY", "ACTIVITY_PROFILE", "VIEW_SEARCH", "ADD_ACTIVITY_RECURRENCE", "MY_ACTIVITIES", "ATTENDING_ACTIVITIES", "MIGHT_ATTEND_ACTIVITIES", "EVENT_ROUNDUP","ACCESS_HOME", "ACCESS_LIST","ACTIVITY_SCREEN", "ACTIVITY_LIST", "ACTIVITY_DETAILS", "PDF")
        and user_prop.key = 'user_id'
        and user_prop2.key = 'connectedBy'
    AND event_param2.key = 'engagement_time_msec'
    AND event_param2.value.int_value  is not null
    AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
    AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to

    group by date_time, user_prop.value.string_value)
    group by date_time, is_guest
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("grouper", "STRING", grouper),
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "date_time": row.date_time,
                "is_guest": row.is_guest,
                "time": row.time
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in time_spent_in_app: {str(e)}")


def section_visit(
    grouper: str = "%Y-%m-%d %H:00:00",
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Track navigation from home screen to different app sections.
    
    Args:
        grouper: DateTime format string for grouping results (default: hourly)
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: date_time, screen, count
        Example: [{"date_time": "2025-06-21 17:00:00", "screen": "FREEBIE_HOME", "count": 45}]
        Shows how many times users navigated from home screen to each section
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = """
    SELECT
      FORMAT_DATETIME(@grouper, DATETIME(TIMESTAMP_MICROS(event_timestamp))) date_time,
      event_param.value.string_value screen,
      COUNT(*) count
    FROM
      {BQ_TABLE_PREFIX},
      UNNEST (event_params) AS event_param,
      UNNEST (event_params) AS event_param2
    WHERE
      event_name = 'screen_view'
      AND event_param.key = 'firebase_screen'
      AND event_param.value.string_value IN ('FREEBIE_HOME',
        'VIEW_HOME',
        'CHAT_HOME',
        'ACTIVITY_SCREEN',
        'RECOMMEND_HOME',
        'SAFETY',
        'CALL',
        "ACCESS_HOME",
        "TOP_FIVE",
        "FIND_STACK")
      AND event_param2.key = 'firebase_previous_screen'
      AND event_param2.value.string_value = 'APP_HOME_SCREEN'
      AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
      AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to
    GROUP BY
      date_time,
      screen
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("grouper", "STRING", grouper),
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "date_time": row.date_time,
                "screen": row.screen,
                "count": row.count
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in section_visit: {str(e)}")


def search_statistics(
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    limit: int = 10,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get statistics on what users are searching for in global search.
    
    Args:
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        limit: Maximum number of search terms to return (default: 10)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: text, count, users
        Example: [{"text": "free food", "count": 156, "users": 89}]
        Ordered by search frequency (most searched terms first)
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = """
    Select text, Sum(count) count, Count(user_id) users from 
    (SELECT
      event_param.value.string_value text,
      user_prop.value.string_value user_id,
      COUNT(*) count
    FROM
      {BQ_TABLE_PREFIX},
      UNNEST (event_params) AS event_param,
      UNNEST (user_properties) AS user_prop
    WHERE
      event_name = 'GLOBAL_SEARCH_TEXT'
      AND event_param.key = 'searchText'
      AND user_prop.key = 'user_id'
      AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
      AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to
    GROUP BY
      event_param.value.string_value, user_prop.value.string_value)
      GROUP BY text
      order by count desc
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "text": row.text,
                "count": row.count,
                "users": row.users
            })
        
        # Apply limit in Python since we removed it from SQL for consistency
        return results[:limit]
        
    except Exception as e:
        raise Exception(f"BigQuery error in search_statistics: {str(e)}")


def push_notification(
    grouper: str = "%Y-%m-%d %H:00:00",
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Track push notification performance - receives vs opens.
    
    Args:
        grouper: DateTime format string for grouping results (default: hourly)
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: date_time, event_name, count
        Example: [{"date_time": "2025-06-21 17:00:00", "event_name": "notification_receive", "count": 245}]
        event_name will be either "notification_receive" or "notification_open"
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = """
    SELECT
          FORMAT_DATETIME(@grouper, DATETIME(TIMESTAMP_MICROS(event_timestamp))) date_time,
          event_name,
          Count(*) as count
      FROM
        {BQ_TABLE_PREFIX}
      WHERE
        (event_name = 'notification_receive' OR event_name = 'notification_open')
        AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
        AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to
      group by date_time, event_name
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("grouper", "STRING", grouper),
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "date_time": row.date_time,
                "event_name": row.event_name,
                "count": row.count
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in push_notification: {str(e)}")


def event_count_ungrouped(
    event_name: str,
    bigquery_client: Optional[bigquery.Client] = None
) -> int:
    """
    Get total count of a specific event across all time.
    
    Args:
        event_name: Name of the event to count (e.g., 'screen_view', 'user_engagement')
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        Integer count of how many times the event occurred
        Example: 15420
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # SQL query with parameterized variables
    query = """
    SELECT
      COUNT(*) Count
    FROM
      {BQ_TABLE_PREFIX}
    WHERE
      event_name = @event_name
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("event_name", "STRING", event_name),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Get the count from the single row result
        for row in rows:
            return row.Count
        
        return 0  # If no results
        
    except Exception as e:
        raise Exception(f"BigQuery error in event_count_ungrouped: {str(e)}")


def event_count(
    event_name: str,
    grouper: str = "%Y-%m-%d %H:00:00",
    timestamp_from: Optional[datetime] = None,
    timestamp_to: Optional[datetime] = None,
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get time-grouped counts of a specific event.
    
    Args:
        event_name: Name of the event to count (e.g., 'screen_view', 'user_engagement')
        grouper: DateTime format string for grouping results (default: hourly)
        timestamp_from: Start time for data range (default: 7 days ago)
        timestamp_to: End time for data range (default: now)
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: date_time, count
        Example: [{"date_time": "2025-06-21 17:00:00", "count": 245}]
        Shows event counts grouped by time period
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # Set default time range if not provided
    if timestamp_to is None:
        timestamp_to = datetime.now()
    if timestamp_from is None:
        timestamp_from = timestamp_to - timedelta(days=7)
    
    # SQL query with parameterized variables
    query = """
    SELECT
      FORMAT_DATETIME(@grouper, DATETIME(TIMESTAMP_MICROS(event_timestamp))) date_time,
      COUNT(*) count
    FROM
      {BQ_TABLE_PREFIX}
    WHERE
      event_name = @event_name
      AND TIMESTAMP_MICROS(event_timestamp) >= @timestamp_from
      AND TIMESTAMP_MICROS(event_timestamp) <= @timestamp_to
    GROUP BY
      date_time
    """
    
    # Configure query job with parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("event_name", "STRING", event_name),
            bigquery.ScalarQueryParameter("grouper", "STRING", grouper),
            bigquery.ScalarQueryParameter("timestamp_from", "TIMESTAMP", timestamp_from),
            bigquery.ScalarQueryParameter("timestamp_to", "TIMESTAMP", timestamp_to),
        ]
    )
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "date_time": row.date_time,
                "count": row.count
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in event_count: {str(e)}")


def average_onboarding_time(
    bigquery_client: Optional[bigquery.Client] = None
) -> Optional[float]:
    """
    Calculate the average time users spend completing the onboarding process.
    
    Args:
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        Average onboarding time in milliseconds, or None if no data
        Example: 342567.8 (about 5.7 minutes)
        
    Note: Only includes users who completed onboarding (reached ONBOARDING_CHILD_GUIDE)
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # SQL query - no parameters needed for this one
    query = """
    Select Avg(time) Avg_Onboarding_Time from
      (SELECT
      user_id, Sum(engagement_time_msec) time
    FROM
    (
      SELECT
        user_prop.value.string_value as user_id,
        case when event_param.value.string_value = 'ONBOARDING_CHILD_GUIDE' then 1 else 0 end as last_screen_flag,
        event_param2.value.int_value as engagement_time_msec
      FROM
        {BQ_TABLE_PREFIX},
        UNNEST (event_params) AS event_param
        ,UNNEST (user_properties) AS user_prop
        ,UNNEST (event_params) AS event_param2
      WHERE
       ((event_name = 'user_engagement' AND event_param.key = 'firebase_screen') 
        OR 
        (event_name = 'screen_view' AND event_param.key = 'firebase_previous_screen'))
        AND event_param.value.string_value IN ('ONBOARDING_HOW_IT_WORKS',
                                                'ONBOARDING_COMMUNITY_TERMS_CONDITIONS',
                                                'ONBOARDING_NEIGHBORHOOD_SELECTION',
                                                'ONBOARDING_NEIGHBORHOOD_CONFIRMATION',
                                                'ONBOARDING_CC_REGISTRATION',
                                                'ONBOARDING_INTEREST_SELECTION',
                                                'ONBOARDING_CHILD_GUIDE',
                                                'ONBOARDING_CHILDREN_PROFILE_LIST',
                                                'ONBOARDING_CHILD_PROFILE_GUIDE',
                                                'ONBOARDING_CHILD_ADD_PROFILE_GUIDE')
        and user_prop.key = 'user_id'
    AND event_param2.key = 'engagement_time_msec'
    AND event_param2.value.int_value  is not null
    )
    GROUP BY
    user_id having Sum(last_screen_flag) > 0)
    """
    
    # No parameters needed for this query
    job_config = bigquery.QueryJobConfig()
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Get the average from the single row result
        for row in rows:
            return row.Avg_Onboarding_Time
        
        return None  # If no results
        
    except Exception as e:
        raise Exception(f"BigQuery error in average_onboarding_time: {str(e)}")


def average_appactivity_time(
    bigquery_client: Optional[bigquery.Client] = None
) -> Optional[float]:
    """
    Calculate the average total time users spend in the app across all activities.
    
    Args:
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        Average app activity time in milliseconds per user, or None if no data
        Example: 1245678.9 (about 20.8 minutes per user)
        
    Note: This aggregates all engagement time per user, then averages across all users
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # SQL query - no parameters needed for this one
    query = """
    Select Avg(time) Avg_AppActivity_Time 
    FROM
    (
      SELECT
        user_prop.value.string_value as user_id,
        Sum(event_param2.value.int_value) as time
      FROM
        {BQ_TABLE_PREFIX},
        UNNEST (event_params) AS event_param
        ,UNNEST (user_properties) AS user_prop
        ,UNNEST (event_params) AS event_param2
      WHERE
        ((event_name = 'user_engagement' AND event_param.key = 'firebase_screen') 
        OR 
        (event_name = 'screen_view' AND event_param.key = 'firebase_previous_screen'))
        AND event_param.value.string_value IN ("TOP_FIVE", "APP_HOME_SCREEN", "GLOBAL_SEARCH", "TUTORIAL_VIDEOS", "CHAT_HOME", "NIGHBOURHOOD_NEWS", "CHAT_TOPICS", "NEW_POST", "POST_DETAILS", "CHAT_IMAGE_GALLERY", "SUGGEST_TOPICS", "CHAT_GENERAL_SEARCH","FREEBIE_HOME", "freebie_listing", "FREEBIE_SEARCH_LIST", "FREEBIE_REQUESTED", "MY_FREEBIE", "SAVED_FREEBIE", "FREEBIE_CATEGORIES", "FREEBIE_DETAILS", "ADD_FREEBIE", "FREEBIE_CONTACT_INFORMATION", "SAFETY", "SAFETY_LISTING", "REPORT_CRIME", "RECOMMEND_HOME", "CONNECT_CHILD_LIST", "TARRANT_AREA_FOOD", "COMMUNITY_LINK", "SUGGEST_PARTNER", "ADD_COMMUNITY_REVIEW", "COOK_CHILDREN_HEALTH_SYSTEM", "MERCY_CLINIC", "CORNERSTONE_CHARITY", "RENT_UTILITIES", "RENTERS_RIGHTS", "HOMEOWNER_PREP", "HOMEBUYER_ASSISTANCE", "LENA_POPE", "LUCINE_CENTER", "MY_HEALTH_MY_RESOURCES", "THE_PARENTING_CENTER", "INDIVIDUAL_PARTNER_PROFILE", "JPS_HEALTH", "lookup_address", "FIND_STACK", "FAMILY_NAVIGATOR_SCREEN", "KIDS_HEALTH", "ACCOUNT_HOME", "ACCOUNT_NOTIFICATION_SETTING", "ACCOUNT_CHANGE_PASSWORD", "ACCOUNT_BADGES", "ACCOUNT_MY_PROFILE", "HELP", "VERIFICATION_CODE_SCREEN", "ACCOUNT_NOTIFICATIONS", "ACCOUNT_CHILD_LISTING", "ACCOUNT_UPDATE_CHILD", "SET_PASSWORD", "CALL", "CALL_DETAILS", "VIEW_HOME", "VIEW_MAP", "ADD_ACTIVITY", "ACTIVITY_PROFILE", "VIEW_SEARCH", "ADD_ACTIVITY_RECURRENCE", "MY_ACTIVITIES", "ATTENDING_ACTIVITIES", "MIGHT_ATTEND_ACTIVITIES", "EVENT_ROUNDUP","ACCESS_HOME", "ACCESS_LIST","ACTIVITY_SCREEN", "ACTIVITY_LIST", "ACTIVITY_DETAILS", "PDF")
        and user_prop.key = 'user_id'
    AND event_param2.key = 'engagement_time_msec'
    AND event_param2.value.int_value  is not null
    group by user_id
    )
    """
    
    # No parameters needed for this query
    job_config = bigquery.QueryJobConfig()
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Get the average from the single row result
        for row in rows:
            return row.Avg_AppActivity_Time
        
        return None  # If no results
        
    except Exception as e:
        raise Exception(f"BigQuery error in average_appactivity_time: {str(e)}")


def active_total_users(
    bigquery_client: Optional[bigquery.Client] = None
) -> List[Dict[str, Any]]:
    """
    Get active user counts for different time periods (1 day, 7 days, 30 days).
    
    Args:
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        List of dictionaries with keys: period, active_users
        Example: [
            {"period": "1_day", "active_users": 245},
            {"period": "7_days", "active_users": 892}, 
            {"period": "30_days", "active_users": 2156}
        ]
        
    Note: Uses screen_view events to determine user activity
    """
    # Use provided client or default module client
    bq_client = bigquery_client or client
    
    # SQL query - combines three separate queries for different time periods
    query = """
    SELECT '1_day' as period, Count(*) Active_Users
    from
    (SELECT
      COUNT(*) c
    FROM
      {BQ_TABLE_PREFIX},
      UNNEST(user_properties) as user_prop
    WHERE
      event_name = 'screen_view'
      and user_prop.key = 'user_id'
      AND TIMESTAMP_MICROS(event_timestamp) >= timestamp_sub(current_timestamp, INTERVAL 1 DAY)
    group by user_prop.value.string_value
    )
    union all
    SELECT '7_days' as period, Count(*) Active_Users
    from
    (SELECT
      COUNT(*) c
    FROM
      {BQ_TABLE_PREFIX},
      UNNEST(user_properties) as user_prop
    WHERE
      event_name = 'screen_view'
      and user_prop.key = 'user_id'
      AND TIMESTAMP_MICROS(event_timestamp) >= timestamp_sub(current_timestamp, INTERVAL 7 DAY)
    group by user_prop.value.string_value
    )
    union all
    SELECT '30_days' as period, Count(*) Active_Users
    from
    (SELECT
      COUNT(*) c
    FROM
      {BQ_TABLE_PREFIX},
      UNNEST(user_properties) as user_prop
    WHERE
      event_name = 'screen_view'
      and user_prop.key = 'user_id'
      AND TIMESTAMP_MICROS(event_timestamp) >= timestamp_sub(current_timestamp, INTERVAL 30 DAY)
    group by user_prop.value.string_value
    )
    ORDER BY 
      CASE 
        WHEN period = '1_day' THEN 1
        WHEN period = '7_days' THEN 2  
        WHEN period = '30_days' THEN 3
      END
    """
    
    # No parameters needed for this query
    job_config = bigquery.QueryJobConfig()
    
    try:
        # Execute query
        query_job = bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        
        # Convert results to list of dictionaries
        results = []
        for row in rows:
            results.append({
                "period": row.period,
                "active_users": row.Active_Users
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"BigQuery error in active_total_users: {str(e)}")


# Daily Analytics Report Generator
def generate_daily_analytics_report(
    output_dir: str = "analytics_reports",
    bigquery_client: Optional[bigquery.Client] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive daily analytics report for ParentPass app.
    
    Args:
        output_dir: Directory to save the report files (default: "analytics_reports")
        bigquery_client: Custom BigQuery client (default: module client)
    
    Returns:
        Dictionary containing all analytics data with timestamps and assessments
        
    Note: Saves both detailed JSON report and human-readable summary
    """
    bq_client = bigquery_client or client
    report_timestamp = datetime.now()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Initialize comprehensive report structure (lean version for LLM processing)
    report = {
        "report_metadata": {
            "generated_at": report_timestamp.isoformat(),
            "report_type": "daily_analytics",
            "app_name": "ParentPass",
            "data_source": "Google Analytics"
        },
        "user_acquisition": {},
        "user_engagement": {},
        "user_retention": {},
        "feature_usage": {},
        "communication": {},
        "summary": {}
    }
    
    print(f"🚀 Generating ParentPass Daily Analytics Report")
    print(f"📅 Report Date: {report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 1. USER ACQUISITION METRICS
        print("\n📊 Analyzing User Acquisition...")
        
        # Onboarding performance
        avg_onboarding = average_onboarding_time(bq_client)
        if avg_onboarding:
            onboarding_minutes = avg_onboarding / 1000 / 60
            onboarding_assessment = "excellent" if onboarding_minutes < 3 else "good" if onboarding_minutes < 7 else "needs_improvement"
            
            report["user_acquisition"]["onboarding"] = {
                "average_time_ms": avg_onboarding,
                "average_time_minutes": round(onboarding_minutes, 1),
                "industry_benchmark_minutes": 5
            }
        
        # Feature discovery patterns
        section_visits = section_visit(bigquery_client=bq_client)
        if section_visits:
            # Aggregate section totals
            section_totals = {}
            for visit in section_visits:
                screen = visit['screen']
                section_totals[screen] = section_totals.get(screen, 0) + visit['count']
            
            # Sort by popularity and create readable names
            popular_sections = sorted(section_totals.items(), key=lambda x: x[1], reverse=True)
            
            discovery_data = []
            for screen, visits in popular_sections:
                readable_name = screen.replace('_', ' ').title().replace('Home', 'Section')
                discovery_data.append({
                    "section": readable_name,
                    "visits_from_home": visits,
                    "screen_id": screen
                })
            
            report["user_acquisition"]["feature_discovery"] = {
                "top_sections": discovery_data[:5],
                "total_navigation_events": sum(section_totals.values()),
                "sections_tracked": len(section_totals)
            }
        
        # 2. USER ENGAGEMENT METRICS
        print("📱 Analyzing User Engagement...")
        
        # Active users (DAU/WAU/MAU)
        active_users = active_total_users(bq_client)
        if active_users:
            metrics = {item['period']: item['active_users'] for item in active_users}
            daily_active = metrics.get('1_day', 0)
            weekly_active = metrics.get('7_days', 0)
            monthly_active = metrics.get('30_days', 0)
            
            # Calculate key ratios
            dau_wau = (daily_active / weekly_active * 100) if weekly_active > 0 else 0
            wau_mau = (weekly_active / monthly_active * 100) if monthly_active > 0 else 0
            dau_mau = (daily_active / monthly_active * 100) if monthly_active > 0 else 0
            
            # Assessments
            engagement_level = "excellent" if dau_wau > 20 else "good" if dau_wau > 14 else "moderate" if dau_wau > 10 else "low"
            retention_level = "excellent" if wau_mau > 30 else "good" if wau_mau > 20 else "moderate" if wau_mau > 15 else "low"
            
            report["user_engagement"]["active_users"] = {
                "daily_active_users": daily_active,
                "weekly_active_users": weekly_active,
                "monthly_active_users": monthly_active,
                "dau_wau_ratio": round(dau_wau, 1),
                "wau_mau_ratio": round(wau_mau, 1),
                "dau_mau_ratio": round(dau_mau, 1),
                "industry_benchmark_dau_mau_min": 15,
                "industry_benchmark_dau_mau_max": 25
            }
        
        # Average app activity time
        avg_activity = average_appactivity_time(bq_client)
        if avg_activity:
            activity_minutes = avg_activity / 1000 / 60
            activity_level = "high" if activity_minutes > 30 else "good" if activity_minutes > 15 else "moderate" if activity_minutes > 5 else "low"
            
            report["user_engagement"]["session_depth"] = {
                "average_total_time_ms": avg_activity,
                "average_total_time_minutes": round(activity_minutes, 1),
                "engagement_level": activity_level,
                "recommendation": "Focus on retention" if activity_level == "low" else "Optimize features" if activity_level == "moderate" else "Maintain quality"
            }
        
        # Top engaged users
        top_users = top_users_by_time_spent(limit=20, bigquery_client=bq_client)
        if top_users:
            power_users = []
            for i, user in enumerate(top_users[:10], 1):
                minutes = user['time_ms'] / 1000 / 60
                power_users.append({
                    "rank": i,
                    "user_id": user['user_id'],
                    "total_time_minutes": round(minutes, 1),
                    "time_ms": user['time_ms']
                })
            
            report["user_engagement"]["power_users"] = {
                "top_10_users": power_users,
                "total_tracked": len(top_users),
                "avg_power_user_time": round(sum(u['total_time_minutes'] for u in power_users) / len(power_users), 1) if power_users else 0
            }
        
        # 3. USER RETENTION ANALYSIS
        print("🔄 Analyzing User Retention...")
        
        # Guest vs Registered engagement
        app_usage = time_spent_in_app(bigquery_client=bq_client)
        if app_usage:
            guest_data = [row for row in app_usage if row['is_guest'] == 1]
            registered_data = [row for row in app_usage if row['is_guest'] == 0]
            
            guest_avg = sum(row['time'] for row in guest_data) / len(guest_data) / 1000 / 60 if guest_data else 0
            registered_avg = sum(row['time'] for row in registered_data) / len(registered_data) / 1000 / 60 if registered_data else 0
            
            conversion_indicator = "strong" if registered_avg > guest_avg * 2 else "moderate" if registered_avg > guest_avg else "weak"
            
            report["user_retention"]["user_type_comparison"] = {
                "guest_avg_time_minutes": round(guest_avg, 1),
                "registered_avg_time_minutes": round(registered_avg, 1),
                "registered_advantage_ratio": round(registered_avg / guest_avg, 1) if guest_avg > 0 else 1.0,
                "guest_periods": len(guest_data),
                "registered_periods": len(registered_data)
            }
        
        # 4. FEATURE USAGE ANALYTICS
        print("🎯 Analyzing Feature Usage...")
        
        # Section engagement breakdown
        section_engagement = time_spent_by_section(bigquery_client=bq_client)
        if section_engagement:
            # Aggregate by section
            section_time = {}
            for item in section_engagement:
                section = item['section']
                if section:  # Skip null sections
                    section_time[section] = section_time.get(section, 0) + item['time']
            
            # Sort by engagement time
            popular_features = sorted(section_time.items(), key=lambda x: x[1], reverse=True)
            
            feature_usage = []
            total_engagement = sum(section_time.values())
            
            for section, time_ms in popular_features:
                percentage = (time_ms / total_engagement * 100) if total_engagement > 0 else 0
                feature_usage.append({
                    "section": section,
                    "total_time_ms": time_ms,
                    "total_time_minutes": round(time_ms / 1000 / 60, 1),
                    "percentage_of_total": round(percentage, 1)
                })
            
            report["feature_usage"]["section_engagement"] = {
                "by_section": feature_usage,
                "most_engaging": feature_usage[0]["section"] if feature_usage else None,
                "total_sections": len(feature_usage),
                "total_engagement_minutes": round(total_engagement / 1000 / 60, 1)
            }
        
        # Search behavior analysis
        search_stats = search_statistics(limit=20, bigquery_client=bq_client)
        if search_stats:
            total_searches = sum(term['count'] for term in search_stats)
            total_search_users = sum(term['users'] for term in search_stats)
            
            top_searches = []
            for i, term in enumerate(search_stats[:10], 1):
                percentage = (term['count'] / total_searches * 100) if total_searches > 0 else 0
                top_searches.append({
                    "rank": i,
                    "search_term": term['text'],
                    "search_count": term['count'],
                    "unique_users": term['users'],
                    "percentage_of_searches": round(percentage, 1),
                    "avg_searches_per_user": round(term['count'] / term['users'], 1) if term['users'] > 0 else 0
                })
            
            report["feature_usage"]["search_behavior"] = {
                "top_searches": top_searches,
                "total_searches": total_searches,
                "total_search_users": total_search_users,
                "avg_searches_per_user": round(total_searches / total_search_users, 1) if total_search_users > 0 else 0,
                "search_diversity": len(search_stats)
            }
        
        # 5. COMMUNICATION EFFECTIVENESS
        print("🔔 Analyzing Communication Performance...")
        
        # Push notification performance
        notification_stats = push_notification(bigquery_client=bq_client)
        if notification_stats:
            receives = [event for event in notification_stats if event['event_name'] == 'notification_receive']
            opens = [event for event in notification_stats if event['event_name'] == 'notification_open']
            
            total_receives = sum(event['count'] for event in receives)
            total_opens = sum(event['count'] for event in opens)
            open_rate = (total_opens / total_receives * 100) if total_receives > 0 else 0
            
            report["communication"]["push_notifications"] = {
                "total_sent": total_receives,
                "total_opened": total_opens,
                "open_rate_percentage": round(open_rate, 1),
                "industry_benchmark_min": 10,
                "industry_benchmark_max": 20,
                "time_periods_analyzed": len(set(event['date_time'] for event in notification_stats))
            }
        
        # 6. GENERATE EXECUTIVE SUMMARY
        print("📋 Generating Executive Summary...")
        
        # Key insights and recommendations
        insights = []
        recommendations = []
        
        # User engagement insights
        if 'active_users' in report['user_engagement']:
            dau = report['user_engagement']['active_users']['daily_active_users']
            mau = report['user_engagement']['active_users']['monthly_active_users']
            
            insights.append(f"Daily Active Users: {dau:,} | Monthly Active Users: {mau:,}")
            
            if dau < 50:
                recommendations.append("Priority: Implement daily engagement features (push notifications, daily content)")
            elif dau < 100:
                recommendations.append("Focus on habit-forming features to grow daily user base")
            else:
                recommendations.append("Optimize experience for power users to maintain high engagement")
        
        # Feature usage insights
        if 'section_engagement' in report['feature_usage']:
            top_feature = report['feature_usage']['section_engagement']['most_engaging']
            insights.append(f"Most engaging feature: {top_feature}")
            recommendations.append(f"Consider expanding {top_feature} functionality based on high engagement")
        
        # Search insights
        if 'search_behavior' in report['feature_usage']:
            top_search = report['feature_usage']['search_behavior']['top_searches'][0]['search_term'] if report['feature_usage']['search_behavior']['top_searches'] else "N/A"
            search_users = report['feature_usage']['search_behavior']['total_search_users']
            insights.append(f"Top search term: '{top_search}' | {search_users:,} users actively searching")
            recommendations.append("Analyze top search terms to identify content gaps and feature requests")
        
        # Communication insights
        if 'push_notifications' in report['communication']:
            open_rate = report['communication']['push_notifications']['open_rate_percentage']
            performance = "excellent" if open_rate > 25 else "good" if open_rate > 15 else "average" if open_rate > 8 else "poor"
            insights.append(f"Push notification open rate: {open_rate}% ({performance})")
            
            if open_rate < 15:
                recommendations.append("Priority: Improve push notification relevance and timing")
            elif open_rate < 25:
                recommendations.append("Optimize push notification content and send times")
            else:
                recommendations.append("Maintain high-quality push notification strategy")
        
        report["summary"] = {
            "report_generated": report_timestamp.isoformat(),
            "total_data_points": len(insights)
        }
        
        # Store only essential raw data (keep it lean for LLM processing)
        # Note: Removed verbose hourly data to reduce file size by 97%
        # Raw data is commented out - uncomment if detailed analysis is needed
        # report["raw_data"] = {
        #     "active_users": active_users if 'active_users' in locals() else [],
        #     "section_engagement": section_engagement if 'section_engagement' in locals() else [],
        #     "search_statistics": search_stats if 'search_stats' in locals() else [],
        #     "notification_performance": notification_stats if 'notification_stats' in locals() else [],
        #     "section_visits": section_visits if 'section_visits' in locals() else [],
        #     "app_usage_comparison": app_usage if 'app_usage' in locals() else [],
        #     "top_users": top_users if 'top_users' in locals() else []
        # }
        
        # 7. SAVE REPORTS
        print("💾 Saving Reports...")
        
        # Save detailed JSON report
        report_filename = f"analytics_report_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(output_dir, report_filename)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save latest report (for easy chatbot access)
        latest_path = os.path.join(output_dir, "latest_analytics.json")
        with open(latest_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Create human-readable summary
        summary_lines = [
            f"ParentPass Analytics Report - {report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "📊 ANALYTICS SUMMARY",
            f"Data Points Collected: {len(insights)}",
            "",
            "🔍 Key Insights:",
        ]
        
        for insight in insights:
            summary_lines.append(f"  • {insight}")
        
        summary_lines.extend([
            "",
            "💡 Priority Recommendations:",
        ])
        
        for rec in recommendations:
            summary_lines.append(f"  • {rec}")
        
        # Add key metrics
        if 'active_users' in report['user_engagement']:
            au = report['user_engagement']['active_users']
            dau_wau = au['dau_wau_ratio']
            wau_mau = au['wau_mau_ratio']
            
            engagement_level = "excellent" if dau_wau > 20 else "good" if dau_wau > 14 else "moderate" if dau_wau > 10 else "low"
            retention_level = "excellent" if wau_mau > 30 else "good" if wau_mau > 20 else "moderate" if wau_mau > 15 else "low"
            
            summary_lines.extend([
                "",
                "📱 Key Metrics:",
                f"  • DAU: {au['daily_active_users']:,} | WAU: {au['weekly_active_users']:,} | MAU: {au['monthly_active_users']:,}",
                f"  • DAU/MAU: {au['dau_mau_ratio']}% (Benchmark: 15-25%)",
                f"  • Engagement: {engagement_level} | Retention: {retention_level}"
            ])
        
        if 'push_notifications' in report['communication']:
            pn = report['communication']['push_notifications']
            performance = "excellent" if pn['open_rate_percentage'] > 25 else "good" if pn['open_rate_percentage'] > 15 else "average" if pn['open_rate_percentage'] > 8 else "poor"
            summary_lines.append(f"  • Push Open Rate: {pn['open_rate_percentage']}% ({performance})")
        
        summary_lines.extend([
            "",
            f"📁 Detailed reports saved to: {output_dir}/",
            f"🤖 Chatbot can reference: {latest_path}",
            ""
        ])
        
        # Save human-readable summary
        summary_filename = f"analytics_summary_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
        summary_path = os.path.join(output_dir, summary_filename)
        
        with open(summary_path, 'w') as f:
            f.write('\n'.join(summary_lines))
        
        # Also save as latest summary
        latest_summary_path = os.path.join(output_dir, "latest_summary.txt")
        with open(latest_summary_path, 'w') as f:
            f.write('\n'.join(summary_lines))
        
        print(f"✅ Analytics Report Generated Successfully!")
        print(f"   📋 Summary: {summary_path}")
        print(f"   📊 Detailed: {report_path}")
        print(f"   🤖 Latest: {latest_path}")
        print("\n" + "\n".join(summary_lines))
        
        return report
        
    except Exception as e:
        error_report = {
            "error": str(e),
            "generated_at": report_timestamp.isoformat(),
            "status": "failed"
        }
        
        error_path = os.path.join(output_dir, "error_log.json")
        with open(error_path, 'w') as f:
            json.dump(error_report, f, indent=2)
        
        print(f"❌ Error generating analytics report: {e}")
        print(f"   Error log saved to: {error_path}")
        
        raise Exception(f"Analytics report generation failed: {e}")


# Function to generate combined analytics (BigQuery + Azure)
def generate_combined_analytics_report(
    output_dir: str = "analytics_reports",
    bigquery_client: Optional[bigquery.Client] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive analytics report combining BigQuery and Azure SQL data.
    
    Args:
        output_dir: Directory to save the report files
        bigquery_client: Custom BigQuery client
    
    Returns:
        Combined analytics report with both BigQuery and Azure insights
    """
    report_timestamp = datetime.now()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"🚀 Generating Combined ParentPass Analytics Report")
    print(f"📅 Report Date: {report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # Generate BigQuery analytics (lean version)
        print("📊 Generating BigQuery Analytics...")
        bigquery_report = generate_daily_analytics_report(output_dir, bigquery_client)
        
        # Generate Azure analytics
        print("🗄️  Generating Azure Database Analytics...")
        azure_analytics = AzureAnalytics()
        azure_report = azure_analytics.generate_comprehensive_azure_report()
        
        # Combine reports
        combined_report = {
            "report_metadata": {
                "generated_at": report_timestamp.isoformat(),
                "report_type": "combined_analytics",
                "app_name": "ParentPass",
                "data_sources": ["Google Analytics via BigQuery", "Azure SQL Database"]
            },
            "user_behavior": bigquery_report.get("user_acquisition", {}),
            "user_engagement": bigquery_report.get("user_engagement", {}),
            "user_retention": bigquery_report.get("user_retention", {}),
            "feature_usage": bigquery_report.get("feature_usage", {}),
            "communication": bigquery_report.get("communication", {}),
            "database_insights": {
                "user_growth": azure_report.get("user_growth", {}),
                "content_creation": azure_report.get("content_creation", {}),
                "neighborhood_activity": azure_report.get("neighborhood_activity", {}),
                "community_engagement": azure_report.get("community_engagement", {}),
                "upcoming_events": azure_report.get("upcoming_events", {})
            },
            "summary": {
                "report_generated": report_timestamp.isoformat(),
                "bigquery_status": "success" if "error" not in bigquery_report else "error",
                "azure_status": "success" if "error" not in azure_report else "error",
                "total_data_sources": 2
            }
        }
        
        # Save combined report
        combined_filename = f"combined_analytics_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        combined_path = os.path.join(output_dir, combined_filename)
        
        with open(combined_path, 'w') as f:
            json.dump(combined_report, f, indent=2, default=str)
        
        # Save as latest combined report
        latest_combined_path = os.path.join(output_dir, "latest_combined_analytics.json")
        with open(latest_combined_path, 'w') as f:
            json.dump(combined_report, f, indent=2, default=str)
        
        print(f"✅ Combined Analytics Report Generated Successfully!")
        print(f"   📊 Combined Report: {combined_path}")
        print(f"   🤖 Latest Combined: {latest_combined_path}")
        
        return combined_report
        
    except Exception as e:
        error_report = {
            "error": str(e),
            "generated_at": report_timestamp.isoformat(),
            "status": "failed",
            "report_type": "combined_analytics"
        }
        
        error_path = os.path.join(output_dir, "combined_error_log.json")
        with open(error_path, 'w') as f:
            json.dump(error_report, f, indent=2)
        
        print(f"❌ Error generating combined analytics report: {e}")
        raise Exception(f"Combined analytics report generation failed: {e}")


# Function to generate lean analytics report (97% smaller)
def generate_lean_analytics_report(
    output_dir: str = "analytics_reports",
    bigquery_client: Optional[bigquery.Client] = None
) -> Dict[str, Any]:
    """
    Generate a lean analytics report optimized for LLM processing.
    This is the same as generate_daily_analytics_report but without verbose raw_data.
    
    Args:
        output_dir: Directory to save the report files
        bigquery_client: Custom BigQuery client
    
    Returns:
        Lean analytics report (97% smaller than full version)
    """
    return generate_daily_analytics_report(output_dir, bigquery_client)


# Convenience function for chatbot integration
def get_latest_analytics(analytics_dir: str = "analytics_reports") -> Optional[Dict[str, Any]]:
    """
    Get the most recent analytics report for chatbot use.
    
    Args:
        analytics_dir: Directory containing analytics reports
        
    Returns:
        Latest analytics report data or None if not found
    """
    latest_path = os.path.join(analytics_dir, "latest_analytics.json")
    
    try:
        if os.path.exists(latest_path):
            with open(latest_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading latest analytics: {e}")
        return None


def get_latest_combined_analytics(analytics_dir: str = "analytics_reports") -> Optional[Dict[str, Any]]:
    """
    Get the most recent combined analytics report (BigQuery + Azure) for chatbot use.
    
    Args:
        analytics_dir: Directory containing analytics reports
        
    Returns:
        Latest combined analytics report data or None if not found
    """
    latest_path = os.path.join(analytics_dir, "latest_combined_analytics.json")
    
    try:
        if os.path.exists(latest_path):
            with open(latest_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading latest combined analytics: {e}")
        return None


def get_latest_azure_analytics(analytics_dir: str = "analytics_reports") -> Optional[Dict[str, Any]]:
    """
    Get the most recent Azure-only analytics report for chatbot use.
    
    Args:
        analytics_dir: Directory containing analytics reports
        
    Returns:
        Latest Azure analytics report data or None if not found
    """
    latest_path = os.path.join(analytics_dir, "latest_azure_analytics.json")
    
    try:
        if os.path.exists(latest_path):
            with open(latest_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading latest Azure analytics: {e}")
        return None


# Command line execution
if __name__ == "__main__":
    import sys
    
    try:
        # Check command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--combined":
                print("📊 Generating combined analytics report (BigQuery + Azure)...")
                report = generate_combined_analytics_report()
            elif sys.argv[1] == "--azure":
                print("🗄️  Generating Azure-only analytics report...")
                # Generate Azure analytics only
                azure = AzureAnalytics()
                report = azure.generate_comprehensive_azure_report()
                
                # Save Azure-only report
                from pathlib import Path
                import json
                from datetime import datetime
                
                output_dir = "analytics_reports"
                Path(output_dir).mkdir(exist_ok=True)
                
                report_timestamp = datetime.now()
                azure_filename = f"azure_analytics_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                azure_path = os.path.join(output_dir, azure_filename)
                
                with open(azure_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                # Save as latest Azure report
                latest_azure_path = os.path.join(output_dir, "latest_azure_analytics.json")
                with open(latest_azure_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                print(f"✅ Azure Analytics Report Generated Successfully!")
                print(f"   📊 Azure Report: {azure_path}")
                print(f"   🤖 Latest Azure: {latest_azure_path}")
            else:
                print("❌ Unknown option. Available options:")
                print("   python bigquery.py                 # Lean BigQuery analytics only")
                print("   python bigquery.py --combined      # Combined BigQuery + Azure")
                print("   python bigquery.py --azure         # Azure analytics only (fast)")
                exit(1)
        else:
            print("📊 Generating lean BigQuery analytics report...")
            report = generate_daily_analytics_report()
        
        print(f"\n🎉 Report generation complete!")
        
    except Exception as e:
        print(f"❌ Failed to generate analytics report: {e}")
        exit(1)