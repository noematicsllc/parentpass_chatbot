"""
Simple analytics data loader - just a switch for categories to files.
"""

import os
from typing import Optional, List
from baml_client.types import AnalyticsCategory


def get_analytics_data_for_category(analytics_category: AnalyticsCategory, analytics_dir: str = "analytics_reports") -> Optional[str]:
    """Simple switch to get analytics data for a category."""
    
    match analytics_category:
        case AnalyticsCategory.CONTENT:
            filenames = ["content_creation.md"]
        case AnalyticsCategory.EVENTS:
            filenames = ["upcoming_events.md"]
        case AnalyticsCategory.REGISTRATIONS:
            filenames = ["new_user_stats.md", "user_registration_trends.md"]
        case AnalyticsCategory.NEIGHBORHOODS:
            filenames = ["neighborhood_distribution.md"]
        case AnalyticsCategory.ENGAGEMENT:
            filenames = ["post_engagement.md", "time_by_section.md", "time_by_user_type.md", 
                        "push_notifications.md", "search_behavior.md", "app_activity_time.md"]
        case AnalyticsCategory.USERS:
            filenames = ["active_users.md", "top_users.md", "onboarding_performance.md", "navigation_patterns.md"]
        case _:
            return None
    
    content_parts = []
    for filename in filenames:
        file_path = os.path.join(analytics_dir, filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    content_parts.append(content)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue
    
    if content_parts:
        return "\n\n".join(content_parts)
    
    return None
