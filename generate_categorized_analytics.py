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
from typing import Dict, Any, List, Tuple

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

# Import analytics functions directly
from app.bigquery import (
    time_spent_by_section, time_spent_in_app, search_statistics, 
    push_notification, active_total_users, average_onboarding_time,
    average_appactivity_time, top_users_by_time_spent, section_visit
)
from app.azure_analytics import AzureAnalytics

# Import BAML client
from baml_client import b


async def summarize_query(query_name: str, description: str, raw_data: Any, data_type: str) -> str:
    """Summarize analytics query using LLM."""
    try:
        return await b.SummarizeAnalyticsQuery(
            query_name=query_name,
            query_description=description,
            raw_data=json.dumps(raw_data, indent=2, default=str),
            data_type=data_type
        )
    except Exception as e:
        return f"Error summarizing {query_name}: {str(e)}"


def get_analytics_categories() -> Dict[str, List[Tuple]]:
    """Define analytics categories and their queries."""
    azure_analytics = AzureAnalytics()
    
    return {
        "content": [
            ("content_creation", "Content Creation Activity",
             "New content creation: activities, posts, freebies", "Content & Community Activity Metrics",
             azure_analytics.get_content_creation_stats)
        ],
        
        "events": [
            ("upcoming_events", "Upcoming Events & Activities",
             "Scheduled events and neighborhood participation", "Event Planning & Community Activity Metrics",
             azure_analytics.get_event_stats)
        ],
        
        "registrations": [
            ("new_user_stats", "New User Registration Statistics",
             "New user registrations across time periods", "User Acquisition & Growth Metrics",
             azure_analytics.get_new_user_stats),
            ("user_registration_trends", "Historical User Registration Trends",
             "Long-term user registration patterns and trends", "User Growth & Trend Analysis",
             azure_analytics.get_historical_user_registration_data)
        ],
        
        "neighborhoods": [
            ("neighborhood_distribution", "Neighborhood Statistics", 
             "User distribution across neighborhoods", "Geographic & Community Distribution Metrics",
             azure_analytics.get_neighborhood_stats)
        ],
        
        "engagement": [
            ("post_engagement", "Post & Comment Engagement",
             "Community interaction through posts and comments", "Community Engagement & Interaction Metrics",
             azure_analytics.get_post_engagement_stats),
            ("time_by_section", "Time Spent by App Section", 
             "User engagement time across app sections", "User Engagement Metrics", 
             time_spent_by_section),
            ("time_by_user_type", "Time Spent by User Type",
             "App engagement time: guest vs registered users", "User Retention & Conversion Metrics", 
             time_spent_in_app),
            ("push_notifications", "Push Notification Performance", 
             "Push notification delivery and open rates", "Communication & Engagement Metrics", 
             push_notification),
            ("search_behavior", "Search Statistics",
             "User search behavior and popular search terms", "User Intent & Behavior Metrics", 
             search_statistics),
            ("app_activity_time", "Average App Activity Time",
             "Average total time users spend in app", "User Engagement & Session Metrics", 
             average_appactivity_time)
        ],
        
        "users": [
            ("active_users", "Active Users Analysis",
             "Daily, Weekly, and Monthly Active User counts", "Core User Engagement Metrics", 
             active_total_users),
            ("top_users", "Top Engaged Users Analysis", 
             "Most engaged users usage patterns", "Power User & Retention Metrics", 
             top_users_by_time_spent),
            ("onboarding_performance", "User Onboarding Performance",
             "Average time to complete onboarding", "User Acquisition & Conversion Metrics", 
             average_onboarding_time),
            ("navigation_patterns", "User Navigation Patterns",
             "User navigation patterns from home screen", "User Navigation & Discovery Metrics", 
             section_visit)
        ]
    }


async def generate_category_files(output_dir: str) -> Dict[str, Dict[str, str]]:
    """Generate analytics files organized by category."""
    print("📊 Generating Categorized Analytics Files...")
    
    categories = get_analytics_categories()
    saved_files = {}
    timestamp = datetime.now()
    
    for category, queries in categories.items():
        print(f"\n📂 Generating {category.upper()} analytics...")
        saved_files[category] = {}
        
        for query_id, name, description, data_type, func in queries:
            print(f"  📄 Generating {name}...")
            
            try:
                # Get raw data
                raw_data = func()
                
                # Handle special cases for single-value functions
                if query_id in ["onboarding_performance", "app_activity_time"]:
                    raw_data = {f"average_{query_id.replace('_performance', '')}_ms": raw_data}
                
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
                
                with open(filepath, 'w') as f:
                    f.write(content)
                
                saved_files[category][query_id] = filepath
                
            except Exception as e:
                print(f"    ❌ Error with {name}: {e}")
    
    return saved_files


async def main():
    """Generate categorized analytics files."""
    print("🚀 Starting Categorized Analytics Generation")
    print("="*50)
    
    # Setup directory - put files directly in analytics_reports
    output_dir = "analytics_reports"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate files by category
        saved_files = await generate_category_files(output_dir)
        
        total_files = sum(len(files) for files in saved_files.values())
        successful_categories = len([cat for cat, files in saved_files.items() if files])
        
        print(f"\n✅ Categorized Analytics Generation Complete!")
        print(f"📂 Categories: {successful_categories}")
        print(f"📄 Total reports: {total_files}")
        print(f"📁 Files saved to: {output_dir}")
        
        # Show category breakdown
        print(f"\n📊 Category Breakdown:")
        for category, files in saved_files.items():
            if files:
                print(f"  {category.title()}: {len(files)} reports")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 