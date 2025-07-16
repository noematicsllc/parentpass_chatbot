#!/usr/bin/env python3
"""
Generate categorized analytics markdown files.
This script runs analytics queries and generates organized markdown files
categorized by analytics type (content, events, users, etc.) rather than
by data source.
Usage:
    python generate_categorized_analytics.py
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Add the app directory to Python path before importing local modules
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

# Import analytics functions directly (after path modification)
from app.bigquery import (  # noqa: E402
    time_spent_by_section,
    time_spent_in_app,
    search_statistics,
    push_notification,
    active_total_users,
    average_onboarding_time,
    average_appactivity_time,
    top_users_by_time_spent,
    section_visit,
)
from app.azure_analytics import AzureAnalytics  # noqa: E402
from baml_client import b  # noqa: E402


def is_valid_data(data: Any) -> bool:
    """Check if data is valid for analysis."""
    if data is None:
        return False
    if isinstance(data, (list, dict)) and len(data) == 0:
        return False
    if isinstance(data, str) and data.strip() == "":
        return False
    return True


def get_function_info(func) -> Dict[str, str]:
    """Get information about a function for error reporting."""
    function_map = {
        # BigQuery functions
        time_spent_by_section: {
            "source": "BigQuery", 
            "description": "User time spent by app section from Firebase Analytics",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        time_spent_in_app: {
            "source": "BigQuery",
            "description": "App engagement time by user type (guest vs registered)",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        search_statistics: {
            "source": "BigQuery",
            "description": "Search behavior and popular search terms",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        push_notification: {
            "source": "BigQuery",
            "description": "Push notification delivery and open rates",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        active_total_users: {
            "source": "BigQuery",
            "description": "Daily, Weekly, and Monthly Active User counts",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        average_onboarding_time: {
            "source": "BigQuery",
            "description": "Average time to complete user onboarding",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        average_appactivity_time: {
            "source": "BigQuery",
            "description": "Average total time users spend in app",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        top_users_by_time_spent: {
            "source": "BigQuery",
            "description": "Most engaged users usage patterns",
            "requirements": "Google Cloud credentials and BigQuery access"
        },
        section_visit: {
            "source": "BigQuery",
            "description": "User navigation patterns from home screen",
            "requirements": "Google Cloud credentials and BigQuery access"
        }
    }
    
    # Handle Azure Analytics methods
    if hasattr(func, '__self__') and isinstance(func.__self__, AzureAnalytics):
        method_name = func.__name__
        azure_methods = {
            "get_content_creation_stats": {
                "source": "Azure SQL Database",
                "description": "Content creation activity: activities, posts, freebies",
                "requirements": "Azure SQL Database connection and credentials"
            },
            "get_event_stats": {
                "source": "Azure SQL Database",
                "description": "Scheduled events and neighborhood participation",
                "requirements": "Azure SQL Database connection and credentials"
            },
            "get_new_user_stats": {
                "source": "Azure SQL Database",
                "description": "New user registrations across time periods",
                "requirements": "Azure SQL Database connection and credentials"
            },
            "get_historical_user_registration_data": {
                "source": "Azure SQL Database",
                "description": "Long-term user registration patterns and trends",
                "requirements": "Azure SQL Database connection and credentials"
            },
            "get_neighborhood_stats": {
                "source": "Azure SQL Database",
                "description": "User distribution across neighborhoods",
                "requirements": "Azure SQL Database connection and credentials"
            },
            "get_post_engagement_stats": {
                "source": "Azure SQL Database",
                "description": "Community interaction through posts and comments",
                "requirements": "Azure SQL Database connection and credentials"
            }
        }
        return azure_methods.get(method_name, {
            "source": "Azure SQL Database",
            "description": f"Azure analytics method: {method_name}",
            "requirements": "Azure SQL Database connection and credentials"
        })
    
    return function_map.get(func, {
        "source": "Unknown",
        "description": f"Analytics function: {getattr(func, '__name__', str(func))}",
        "requirements": "Database connection and proper credentials"
    })


# Import BAML client
async def summarize_query(
    query_name: str, description: str, raw_data: Any, data_type: str
) -> str:
    """Summarize analytics query using LLM."""
    try:
        return await b.SummarizeAnalyticsQuery(
            query_name=query_name,
            query_description=description,
            raw_data=json.dumps(raw_data, indent=2, default=str),
            data_type=data_type,
        )
    except Exception as e:
        return f"Error summarizing {query_name}: {str(e)}"


def get_analytics_categories() -> Dict[str, List[Tuple]]:
    """Define analytics categories and their queries."""
    azure_analytics = AzureAnalytics()
    return {
        "content": [
            (
                "content_creation",
                "Content Creation Activity",
                "New content creation: activities, posts, freebies",
                "Content & Community Activity Metrics",
                azure_analytics.get_content_creation_stats,
            )
        ],
        "events": [
            (
                "upcoming_events",
                "Upcoming Events & Activities",
                "Scheduled events and neighborhood participation",
                "Event Planning & Community Activity Metrics",
                azure_analytics.get_event_stats,
            )
        ],
        "registrations": [
            (
                "new_user_stats",
                "New User Registration Statistics",
                "New user registrations across time periods",
                "User Acquisition & Growth Metrics",
                azure_analytics.get_new_user_stats,
            ),
            (
                "user_registration_trends",
                "Historical User Registration Trends",
                "Long-term user registration patterns and trends",
                "User Growth & Trend Analysis",
                azure_analytics.get_historical_user_registration_data,
            ),
        ],
        "neighborhoods": [
            (
                "neighborhood_distribution",
                "Neighborhood Statistics",
                "User distribution across neighborhoods",
                "Geographic & Community Distribution Metrics",
                azure_analytics.get_neighborhood_stats,
            )
        ],
        "engagement": [
            (
                "post_engagement",
                "Post & Comment Engagement",
                "Community interaction through posts and comments",
                "Community Engagement & Interaction Metrics",
                azure_analytics.get_post_engagement_stats,
            ),
            (
                "time_by_section",
                "Time Spent by App Section",
                "User engagement time across app sections",
                "User Engagement Metrics",
                time_spent_by_section,
            ),
            (
                "time_by_user_type",
                "Time Spent by User Type",
                "App engagement time: guest vs registered users",
                "User Retention & Conversion Metrics",
                time_spent_in_app,
            ),
            (
                "push_notifications",
                "Push Notification Performance",
                "Push notification delivery and open rates",
                "Communication & Engagement Metrics",
                push_notification,
            ),
            (
                "search_behavior",
                "Search Statistics",
                "User search behavior and popular search terms",
                "User Intent & Behavior Metrics",
                search_statistics,
            ),
            (
                "app_activity_time",
                "Average App Activity Time",
                "Average total time users spend in app",
                "User Engagement & Session Metrics",
                average_appactivity_time,
            ),
        ],
        "users": [
            (
                "active_users",
                "Active Users Analysis",
                "Daily, Weekly, and Monthly Active User counts",
                "Core User Engagement Metrics",
                active_total_users,
            ),
            (
                "top_users",
                "Top Engaged Users Analysis",
                "Most engaged users usage patterns",
                "Power User & Retention Metrics",
                top_users_by_time_spent,
            ),
            (
                "onboarding_performance",
                "User Onboarding Performance",
                "Average time to complete onboarding",
                "User Acquisition & Conversion Metrics",
                average_onboarding_time,
            ),
            (
                "navigation_patterns",
                "User Navigation Patterns",
                "User navigation patterns from home screen",
                "User Navigation & Discovery Metrics",
                section_visit,
            ),
        ],
    }


async def generate_category_files(output_dir: str) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """Generate analytics files organized by category."""
    print("📊 Generating Categorized Analytics Files...")

    categories = get_analytics_categories()
    saved_files = {}
    failed_reports = {}
    timestamp = datetime.now()

    for category, queries in categories.items():
        print(f"\n📂 Generating {category.upper()} analytics...")
        saved_files[category] = {}
        failed_reports[category] = {}

        for query_id, name, description, data_type, func in queries:
            print(f"  📄 Generating {name}...")

            try:
                # Get raw data
                raw_data = func()

                # Handle special cases for single-value functions
                if query_id in ["onboarding_performance", "app_activity_time"]:
                    raw_data = {
                        f"average_{query_id.replace('_performance', '')}_ms": raw_data
                    }

                # Check if data is valid
                if not is_valid_data(raw_data):
                    print(f"    ⚠️  No data returned for {name}")
                    
                    # Get function information for failure report
                    func_info = get_function_info(func)
                    
                    # Create failure report
                    filename = f"{query_id}_FAILED.md"
                    filepath = os.path.join(output_dir, filename)
                    
                    content = f"""# {name} - DATA UNAVAILABLE

**Category:** {category.title()}
**Status:** ❌ FAILED - No Data Available
**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Failure Details

**Data Source:** {func_info.get('source', 'Unknown')}
**Expected Data:** {func_info.get('description', 'No description available')}
**Requirements:** {func_info.get('requirements', 'Unknown requirements')}

## Raw Response
```
{raw_data if raw_data is not None else 'None'}
```

## Function Details
- **Function:** {getattr(func, '__name__', str(func))}
- **Module:** {getattr(func, '__module__', 'Unknown')}

## Troubleshooting
1. Check database connection and credentials
2. Verify required environment variables are set
3. Ensure data source contains the expected data
4. Check for any authentication or permission issues

---
*Generated by ParentPass Analytics System - Failure Report*
"""
                    
                    with open(filepath, "w") as f:
                        f.write(content)
                    
                    failed_reports[category][query_id] = filepath
                    continue

                # Summarize with LLM
                summary = await summarize_query(name, description, raw_data, data_type)

                # Save as markdown with clean filename
                filename = f"{query_id}.md"
                filepath = os.path.join(output_dir, filename)

                content = f"""# {name}

**Category:** {category.title()}
**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Analytics Summary

{summary}

---
*Generated by ParentPass Analytics System*
"""

                with open(filepath, "w") as f:
                    f.write(content)

                saved_files[category][query_id] = filepath
                print(f"    ✅ Generated {name}")

            except Exception as e:
                print(f"    ❌ Error with {name}: {e}")
                
                # Get function information for failure report
                func_info = get_function_info(func)
                
                # Create error report
                filename = f"{query_id}_ERROR.md"
                filepath = os.path.join(output_dir, filename)
                
                content = f"""# {name} - ERROR

**Category:** {category.title()}
**Status:** ❌ ERROR
**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Error Details

**Data Source:** {func_info.get('source', 'Unknown')}
**Expected Data:** {func_info.get('description', 'No description available')}
**Requirements:** {func_info.get('requirements', 'Unknown requirements')}

## Error Message
```
{str(e)}
```

## Function Details
- **Function:** {getattr(func, '__name__', str(func))}
- **Module:** {getattr(func, '__module__', 'Unknown')}

## Troubleshooting
1. Check the error message above for specific issues
2. Verify database connection and credentials
3. Check required environment variables
4. Ensure all dependencies are installed and accessible

---
*Generated by ParentPass Analytics System - Error Report*
"""
                
                with open(filepath, "w") as f:
                    f.write(content)
                
                failed_reports[category][query_id] = filepath

    return saved_files, failed_reports


async def main():
    """Generate categorized analytics files."""
    print("🚀 Starting Categorized Analytics Generation")
    print("=" * 50)

    # Setup directory - put files directly in analytics_reports
    output_dir = "analytics_reports"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        # Generate files by category
        saved_files, failed_reports = await generate_category_files(output_dir)

        successful_files = sum(len(files) for files in saved_files.values())
        failed_files = sum(len(files) for files in failed_reports.values())
        total_files = successful_files + failed_files
        successful_categories = len([cat for cat, files in saved_files.items() if files])

        print("\n" + "=" * 50)
        print("📊 Analytics Generation Complete!")
        print(f"📂 Categories processed: {len(saved_files)}")
        print(f"✅ Successful reports: {successful_files}")
        print(f"❌ Failed reports: {failed_files}")
        print(f"📄 Total reports: {total_files}")
        print(f"📁 Files saved to: {output_dir}")

        # Show detailed breakdown
        print("\n📈 Success Breakdown:")
        for category, files in saved_files.items():
            if files:
                print(f"  ✅ {category.title()}: {len(files)} reports")

        if any(files for files in failed_reports.values()):
            print("\n⚠️  Failed Reports:")
            for category, files in failed_reports.items():
                if files:
                    print(f"  ❌ {category.title()}: {len(files)} failures")
                    for query_id, filepath in files.items():
                        print(f"     - {query_id}")

        # Show data source summary
        bigquery_failures = 0
        azure_failures = 0
        for category_failures in failed_reports.values():
            for filepath in category_failures.values():
                with open(filepath, 'r') as f:
                    content = f.read()
                    if "BigQuery" in content:
                        bigquery_failures += 1
                    elif "Azure SQL" in content:
                        azure_failures += 1

        if bigquery_failures > 0 or azure_failures > 0:
            print(f"\n🔍 Data Source Issues:")
            if bigquery_failures > 0:
                print(f"  🚨 BigQuery: {bigquery_failures} failures (check Google Cloud authentication)")
            if azure_failures > 0:
                print(f"  🚨 Azure SQL: {azure_failures} failures (check Azure database connection)")

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
