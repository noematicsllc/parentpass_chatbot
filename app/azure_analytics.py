from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from database import AzureSQLReadOnlyConnection


class AzureAnalytics:
    """Azure SQL Database analytics for ParentPass community data"""

    def __init__(self, db_connection: Optional[AzureSQLReadOnlyConnection] = None):
        self.db = db_connection or AzureSQLReadOnlyConnection()

    def get_new_user_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get new user registration statistics for different time periods.
        Includes both rolling periods (last 7 days, last 30 days) and
        calendar periods (current week, current month, etc.).

        Args:
            days_back: How many days back to analyze (default: 30)

        Returns:
            Dictionary with new user counts by time period
        """
        query = """
        WITH DateRanges AS (
            SELECT
                GETDATE() as now_date,
                -- Rolling periods
                DATEADD(day, -7, GETDATE()) as week_ago,
                DATEADD(day, -30, GETDATE()) as month_ago,
                DATEADD(day, -365, GETDATE()) as year_ago,
                -- Calendar periods
                DATEADD(week, DATEDIFF(week, 0, GETDATE()), 0) as current_week_start,
                DATEADD(week, DATEDIFF(week, 0, GETDATE()) - 1, 0) as last_week_start,
                DATEADD(week, DATEDIFF(week, 0, GETDATE()), 0) as last_week_end,
                DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) as current_month_start,
                DATEFROMPARTS(
                    YEAR(DATEADD(month, -1, GETDATE())),
                    MONTH(DATEADD(month, -1, GETDATE())),
                    1
                ) as last_month_start,
                EOMONTH(DATEADD(month, -1, GETDATE())) as last_month_end,
                DATEFROMPARTS(YEAR(GETDATE()), 1, 1) as current_year_start,
                DATEFROMPARTS(YEAR(GETDATE()) - 1, 1, 1) as last_year_start,
                DATEFROMPARTS(YEAR(GETDATE()) - 1, 12, 31) as last_year_end
        )
        -- Rolling periods (existing logic)
        SELECT
            'rolling_last_7_days' as period,
            COUNT(*) as new_users,
            'Rolling' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.week_ago
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'rolling_previous_7_days' as period,
            COUNT(*) as new_users,
            'Rolling' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= DATEADD(day, -7, d.week_ago)
            AND a.CreatedOn < d.week_ago
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'rolling_last_30_days' as period,
            COUNT(*) as new_users,
            'Rolling' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.month_ago
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'rolling_previous_30_days' as period,
            COUNT(*) as new_users,
            'Rolling' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= DATEADD(month, -1, d.month_ago)
            AND a.CreatedOn < d.month_ago
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'rolling_last_365_days' as period,
            COUNT(*) as new_users,
            'Rolling' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.year_ago
            AND a.IsActive = 1

        -- Calendar periods (new)
        UNION ALL

        SELECT
            'calendar_current_week' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.current_week_start
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'calendar_last_week' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.last_week_start
            AND a.CreatedOn < d.current_week_start
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'calendar_current_month' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.current_month_start
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'calendar_last_month' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.last_month_start
            AND a.CreatedOn <= d.last_month_end
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'calendar_current_year' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.current_year_start
            AND a.IsActive = 1

        UNION ALL

        SELECT
            'calendar_last_year' as period,
            COUNT(*) as new_users,
            'Calendar' as period_type
        FROM Accounts a, DateRanges d
        WHERE a.CreatedOn >= d.last_year_start
            AND a.CreatedOn <= d.last_year_end
            AND a.IsActive = 1
        """

        try:
            results = self.db.execute_query(query)

            # Organize results by period type for better structure
            organized_results = {
                "rolling_periods": {},
                "calendar_periods": {},
                "all_periods": {},
            }

            for row in results:
                period = row["period"]
                new_users = row["new_users"]
                period_type = row["period_type"]

                # Add to appropriate category
                if period_type == "Rolling":
                    organized_results["rolling_periods"][period] = new_users
                elif period_type == "Calendar":
                    organized_results["calendar_periods"][period] = new_users

                # Also add to flat structure for backward compatibility
                organized_results["all_periods"][period] = new_users

            return organized_results

        except Exception as e:
            print(f"Error getting new user stats: {e}")
            return {"rolling_periods": {}, "calendar_periods": {}, "all_periods": {}}

    def get_historical_user_registration_data(
        self, period_type: str = "month", periods_back: int = 12
    ) -> Dict[str, Any]:
        """
        Get historical user registration data in a table format for trend analysis.

        Args:
            period_type: Type of period to analyze ('week', 'month', 'year')
            periods_back: Number of periods to go back (default: 12)

        Returns:
            Dictionary with historical registration data and metadata
        """

        if period_type not in ["week", "month", "year"]:
            raise ValueError("period_type must be 'week', 'month', or 'year'")

        if period_type == "week":
            # Weekly data - calendar weeks (Monday to Sunday)
            query = """
            WITH Numbers AS (
                SELECT 0 as number
                UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
                UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
                UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14
                UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19
                UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
                UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29
                UNION ALL SELECT 30 UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34
                UNION ALL SELECT 35 UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
                UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44
                UNION ALL SELECT 45 UNION ALL SELECT 46 UNION ALL SELECT 47 UNION ALL SELECT 48 UNION ALL SELECT 49
                UNION ALL SELECT 50 UNION ALL SELECT 51 UNION ALL SELECT 52
            ),
            WeekSeries AS (
                SELECT
                    DATEADD(week, -n.number, DATEADD(week, DATEDIFF(week, 0, GETDATE()), 0)) as week_start,
                    DATEADD(day, 6,
                        DATEADD(week, -n.number,
                            DATEADD(week, DATEDIFF(week, 0, GETDATE()), 0)
                        )
                    ) as week_end,
                    n.number as weeks_ago
                FROM Numbers n
                WHERE n.number BETWEEN 0 AND ?
            ),
            WeeklyRegistrations AS (
                SELECT
                    ws.week_start,
                    ws.week_end,
                    ws.weeks_ago,
                    COUNT(a.Id) as new_users,
                    CONCAT(YEAR(ws.week_start), '-W', FORMAT(DATEPART(week, ws.week_start), '00')) as period_label
                FROM WeekSeries ws
                LEFT JOIN Accounts a ON a.CreatedOn >= ws.week_start
                    AND a.CreatedOn < DATEADD(day, 1, ws.week_end)
                    AND a.IsActive = 1
                GROUP BY ws.week_start, ws.week_end, ws.weeks_ago
            )
            SELECT
                period_label,
                week_start as period_start,
                week_end as period_end,
                new_users,
                weeks_ago as periods_ago,
                SUM(new_users) OVER (ORDER BY weeks_ago DESC) as cumulative_users
            FROM WeeklyRegistrations
            ORDER BY weeks_ago
            """

        elif period_type == "month":
            # Monthly data - calendar months
            query = """
            WITH Numbers AS (
                SELECT 0 as number
                UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
                UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
                UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14
                UNION ALL SELECT 15 UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19
                UNION ALL SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24
                UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29
                UNION ALL SELECT 30 UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34
                UNION ALL SELECT 35 UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39
                UNION ALL SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44
                UNION ALL SELECT 45 UNION ALL SELECT 46 UNION ALL SELECT 47 UNION ALL SELECT 48 UNION ALL SELECT 49
                UNION ALL SELECT 50 UNION ALL SELECT 51 UNION ALL SELECT 52 UNION ALL SELECT 53 UNION ALL SELECT 54
                UNION ALL SELECT 55 UNION ALL SELECT 56 UNION ALL SELECT 57 UNION ALL SELECT 58 UNION ALL SELECT 59
                UNION ALL SELECT 60 UNION ALL SELECT 61 UNION ALL SELECT 62 UNION ALL SELECT 63 UNION ALL SELECT 64
                UNION ALL SELECT 65 UNION ALL SELECT 66 UNION ALL SELECT 67 UNION ALL SELECT 68 UNION ALL SELECT 69
                UNION ALL SELECT 70 UNION ALL SELECT 71 UNION ALL SELECT 72
            ),
            MonthSeries AS (
                SELECT
                    DATEFROMPARTS(
                        YEAR(DATEADD(month, -n.number, GETDATE())),
                        MONTH(DATEADD(month, -n.number, GETDATE())),
                        1
                    ) as month_start,
                    EOMONTH(DATEADD(month, -n.number, GETDATE())) as month_end,
                    n.number as months_ago
                FROM Numbers n
                WHERE n.number BETWEEN 0 AND ?
            ),
            MonthlyRegistrations AS (
                SELECT
                    ms.month_start,
                    ms.month_end,
                    ms.months_ago,
                    COUNT(a.Id) as new_users,
                    FORMAT(ms.month_start, 'yyyy-MM') as period_label
                FROM MonthSeries ms
                LEFT JOIN Accounts a ON a.CreatedOn >= ms.month_start
                    AND a.CreatedOn <= ms.month_end
                    AND a.IsActive = 1
                GROUP BY ms.month_start, ms.month_end, ms.months_ago
            )
            SELECT
                period_label,
                month_start as period_start,
                month_end as period_end,
                new_users,
                months_ago as periods_ago,
                SUM(new_users) OVER (ORDER BY months_ago DESC) as cumulative_users
            FROM MonthlyRegistrations
            ORDER BY months_ago
            """

        else:  # year
            # Yearly data - calendar years
            query = """
            WITH Numbers AS (
                SELECT 0 as number
                UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
                UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
                UNION ALL SELECT 10
            ),
            YearSeries AS (
                SELECT
                    DATEFROMPARTS(YEAR(GETDATE()) - n.number, 1, 1) as year_start,
                    DATEFROMPARTS(YEAR(GETDATE()) - n.number, 12, 31) as year_end,
                    n.number as years_ago
                FROM Numbers n
                WHERE n.number BETWEEN 0 AND ?
            ),
            YearlyRegistrations AS (
                SELECT
                    ys.year_start,
                    ys.year_end,
                    ys.years_ago,
                    COUNT(a.Id) as new_users,
                    CAST(YEAR(ys.year_start) AS VARCHAR) as period_label
                FROM YearSeries ys
                LEFT JOIN Accounts a ON a.CreatedOn >= ys.year_start
                    AND a.CreatedOn <= ys.year_end
                    AND a.IsActive = 1
                GROUP BY ys.year_start, ys.year_end, ys.years_ago
            )
            SELECT
                period_label,
                year_start as period_start,
                year_end as period_end,
                new_users,
                years_ago as periods_ago,
                SUM(new_users) OVER (ORDER BY years_ago DESC) as cumulative_users
            FROM YearlyRegistrations
            ORDER BY years_ago
            """

        try:
            results = self.db.execute_query(query, (periods_back - 1,))

            # Process results into a structured format
            historical_data = []
            total_users = 0

            for row in results:
                period_data = {
                    "period_label": row["period_label"],
                    "period_start": (
                        row["period_start"].isoformat() if row["period_start"] else None
                    ),
                    "period_end": (
                        row["period_end"].isoformat() if row["period_end"] else None
                    ),
                    "new_users": row["new_users"],
                    "periods_ago": row["periods_ago"],
                    "cumulative_users": row["cumulative_users"],
                }
                historical_data.append(period_data)
                total_users += row["new_users"]

            # Calculate some basic statistics
            if historical_data:
                user_counts = [period["new_users"] for period in historical_data]
                avg_per_period = sum(user_counts) / len(user_counts)
                max_period = max(historical_data, key=lambda x: x["new_users"])
                min_period = min(historical_data, key=lambda x: x["new_users"])

                # Calculate growth trend (simple linear trend)
                if len(historical_data) >= 2:
                    recent_avg = sum(user_counts[-3:]) / min(
                        3, len(user_counts)
                    )  # Last 3 periods
                    older_avg = sum(user_counts[:3]) / min(
                        3, len(user_counts)
                    )  # First 3 periods
                    trend_direction = (
                        "growing"
                        if recent_avg > older_avg
                        else "declining" if recent_avg < older_avg else "stable"
                    )
                else:
                    trend_direction = "insufficient_data"
            else:
                avg_per_period = 0
                max_period = None
                min_period = None
                trend_direction = "no_data"

            return {
                "metadata": {
                    "period_type": period_type,
                    "periods_back": periods_back,
                    "total_periods": len(historical_data),
                    "generated_at": datetime.now().isoformat(),
                },
                "summary_stats": {
                    "total_users_in_period": total_users,
                    "average_per_period": round(avg_per_period, 1),
                    "trend_direction": trend_direction,
                    "highest_period": {
                        "period": max_period["period_label"] if max_period else None,
                        "count": max_period["new_users"] if max_period else 0,
                    },
                    "lowest_period": {
                        "period": min_period["period_label"] if min_period else None,
                        "count": min_period["new_users"] if min_period else 0,
                    },
                },
                "historical_data": historical_data,
            }

        except Exception as e:
            print(f"Error getting historical user registration data: {e}")
            return {
                "metadata": {
                    "period_type": period_type,
                    "periods_back": periods_back,
                    "error": str(e),
                },
                "summary_stats": {},
                "historical_data": [],
            }

    def get_content_creation_stats(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Get statistics on new content creation (activities, posts, freebies).

        Args:
            days_back: How many days back to analyze (default: 7)

        Returns:
            Dictionary with content creation stats by category
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        query = """
        WITH ContentStats AS (
            -- Activities/Events
            SELECT
                'activities' as content_type,
                COUNT(*) as count,
                'Events and activities for families' as description
            FROM Activities
            WHERE CreatedOn >= ? AND IsActive = 1

            UNION ALL

            -- Children Activities (at-home activities)
            SELECT
                'children_activities' as content_type,
                COUNT(*) as count,
                'At-home activities for children' as description
            FROM ChildrenActivities
            WHERE CreatedOn >= ? AND IsActive = 1

            UNION ALL

            -- Access content (parent reading materials)
            SELECT
                'access_content' as content_type,
                COUNT(*) as count,
                'Parent reading materials and resources' as description
            FROM Accesses
            WHERE CreatedOn >= ? AND IsActive = 1

            UNION ALL

            -- Education Support resources
            SELECT
                'education_support' as content_type,
                COUNT(*) as count,
                'Educational support resources' as description
            FROM EducationSupports
            WHERE CreatedOn >= ? AND IsActive = 1

            UNION ALL

            -- Community Posts
            SELECT
                'posts' as content_type,
                COUNT(*) as count,
                'Community posts and discussions' as description
            FROM Posts
            WHERE CreatedOn >= ? AND IsActive = 1

            UNION ALL

            -- Freebies
            SELECT
                'freebies' as content_type,
                COUNT(*) as count,
                'Free items and giveaways' as description
            FROM Freebies
            WHERE CreatedOn >= ? AND IsActive = 1
        )
        SELECT
            content_type,
            count,
            description,
            CASE
                WHEN content_type IN ('activities', 'children_activities', 'access_content', 'education_support')
                THEN 'official_content'
                ELSE 'community_content'
            END as category
        FROM ContentStats
        ORDER BY count DESC
        """

        try:
            params = tuple([cutoff_date] * 6)  # Same date for all 6 queries
            results = self.db.execute_query(query, params)

            # Organize results
            stats = {
                "time_period_days": days_back,
                "cutoff_date": cutoff_date.isoformat(),
                "by_type": {},
                "totals": {
                    "official_content": 0,
                    "community_content": 0,
                    "all_content": 0,
                },
            }

            for row in results:
                stats["by_type"][row["content_type"]] = {
                    "count": row["count"],
                    "description": row["description"],
                    "category": row["category"],
                }
                stats["totals"][row["category"]] += row["count"]
                stats["totals"]["all_content"] += row["count"]

            return stats

        except Exception as e:
            print(f"Error getting content creation stats: {e}")
            return {}

    def get_neighborhood_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get high-level neighborhood statistics.

        Args:
            days_back: How many days back to analyze for trends (default: 30)

        Returns:
            Dictionary with neighborhood stats summary
        """
        query = """
        WITH NeighborhoodCounts AS (
            SELECT
                COUNT(DISTINCT n.Id) as total_neighborhoods,
                COUNT(DISTINCT pp.Id) as total_users,
                AVG(CAST(user_counts.user_count AS FLOAT)) as avg_users_per_neighborhood,
                MAX(user_counts.user_count) as max_users_in_neighborhood,
                MIN(user_counts.user_count) as min_users_in_neighborhood
            FROM Neighborhoods n
            LEFT JOIN ParentProfiles pp ON n.Id = pp.NeighborhoodId
            LEFT JOIN Accounts acc ON pp.Id = acc.ParentProfileId
            LEFT JOIN (
                SELECT pp2.NeighborhoodId, COUNT(*) as user_count
                FROM ParentProfiles pp2
                INNER JOIN Accounts acc2 ON pp2.Id = acc2.ParentProfileId
                WHERE acc2.IsActive = 1 AND pp2.IsActive = 1
                GROUP BY pp2.NeighborhoodId
            ) user_counts ON n.Id = user_counts.NeighborhoodId
            WHERE n.IsActive = 1 AND acc.IsActive = 1 AND pp.IsActive = 1
        ),
        TopNeighborhood AS (
            SELECT TOP 1
                n.Name as most_populous_neighborhood,
                COUNT(*) as user_count
            FROM Neighborhoods n
            INNER JOIN ParentProfiles pp ON n.Id = pp.NeighborhoodId
            INNER JOIN Accounts acc ON pp.Id = acc.ParentProfileId
            WHERE n.IsActive = 1 AND acc.IsActive = 1 AND pp.IsActive = 1
            GROUP BY n.Id, n.Name
            ORDER BY COUNT(*) DESC
        )
        SELECT
            nc.total_neighborhoods,
            nc.total_users,
            ROUND(nc.avg_users_per_neighborhood, 1) as avg_users_per_neighborhood,
            nc.max_users_in_neighborhood,
            nc.min_users_in_neighborhood,
            tn.most_populous_neighborhood,
            tn.user_count as most_populous_user_count
        FROM NeighborhoodCounts nc
        CROSS JOIN TopNeighborhood tn
        """

        try:
            results = self.db.execute_query(query)

            if results:
                stats = results[0]
                return {
                    "total_neighborhoods": stats["total_neighborhoods"],
                    "total_users": stats["total_users"],
                    "avg_users_per_neighborhood": stats["avg_users_per_neighborhood"],
                    "most_populous_neighborhood": stats["most_populous_neighborhood"],
                    "most_populous_user_count": stats["most_populous_user_count"],
                    "user_distribution": {
                        "max_users": stats["max_users_in_neighborhood"],
                        "min_users": stats["min_users_in_neighborhood"],
                        "average": stats["avg_users_per_neighborhood"],
                    },
                }
            else:
                return {}

        except Exception as e:
            print(f"Error getting neighborhood stats: {e}")
            return {}

    def get_post_engagement_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get post and comment engagement statistics.

        Args:
            days_back: How many days back to analyze (default: 30)

        Returns:
            Dictionary with post engagement metrics
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        query = """
        WITH PostStats AS (
            SELECT
                COUNT(DISTINCT p.Id) as total_posts,
                COUNT(DISTINCT c.Id) as total_comments,
                COUNT(DISTINCT p.AccountId) as unique_posters,
                COUNT(DISTINCT c.AccountId) as unique_commenters
            FROM Posts p
            LEFT JOIN Comments c ON p.Id = c.PostId AND c.CreatedOn >= ? AND c.IsActive = 1
            WHERE p.CreatedOn >= ? AND p.IsActive = 1
        ),
        ResponseStats AS (
            SELECT
                p.Id as post_id,
                COUNT(c.Id) as comment_count
            FROM Posts p
            LEFT JOIN Comments c ON p.Id = c.PostId AND c.IsActive = 1
            WHERE p.CreatedOn >= ? AND p.IsActive = 1
            GROUP BY p.Id
        ),
        EngagementMetrics AS (
            SELECT
                COUNT(*) as posts_with_responses,
                AVG(CAST(comment_count AS FLOAT)) as avg_comments_per_post,
                MAX(comment_count) as max_comments_on_post
            FROM ResponseStats
            WHERE comment_count > 0
        )
        SELECT
            ps.total_posts,
            ps.total_comments,
            ps.unique_posters,
            ps.unique_commenters,
            COALESCE(em.posts_with_responses, 0) as posts_with_responses,
            COALESCE(em.avg_comments_per_post, 0) as avg_comments_per_post,
            COALESCE(em.max_comments_on_post, 0) as max_comments_on_post,
            CASE
                WHEN ps.total_posts > 0
                THEN ROUND(CAST(COALESCE(em.posts_with_responses, 0) AS FLOAT) / ps.total_posts * 100, 2)
                ELSE 0
            END as response_rate_percentage
        FROM PostStats ps
        CROSS JOIN EngagementMetrics em
        """

        try:
            params = (cutoff_date, cutoff_date, cutoff_date)
            results = self.db.execute_query(query, params)

            if results:
                stats = results[0]
                stats["time_period_days"] = days_back
                stats["cutoff_date"] = cutoff_date.isoformat()
                return dict(stats)
            else:
                return {
                    "time_period_days": days_back,
                    "cutoff_date": cutoff_date.isoformat(),
                }

        except Exception as e:
            print(f"Error getting post engagement stats: {e}")
            return {}

    def get_event_stats(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Get high-level statistics about upcoming events.

        Args:
            days_ahead: How many days ahead to look (default: 30)

        Returns:
            Dictionary with event count statistics by time period
        """
        end_date = datetime.now() + timedelta(days=days_ahead)
        week_ahead = datetime.now() + timedelta(days=7)

        query = """
        WITH EventCounts AS (
            SELECT
                COUNT(*) as total_events,
                COUNT(CASE WHEN a.StartDate <= ? THEN 1 END) as next_week_count,
                COUNT(CASE WHEN a.StartDate > ? AND a.StartDate <= ? THEN 1 END) as next_month_count,
                COUNT(DISTINCT a.Type) as event_types,
                COUNT(DISTINCT a.NeighborhoodId) as neighborhoods_with_events,
                AVG(CASE WHEN a.Cost IS NOT NULL AND a.Cost > 0 THEN a.Cost END) as avg_event_cost,
                COUNT(CASE WHEN a.Cost = 0 OR a.Cost IS NULL THEN 1 END) as free_events_count
            FROM Activities a
            WHERE a.StartDate >= GETDATE()
                AND a.StartDate <= ?
                AND a.IsActive = 1
        )
        SELECT
            total_events,
            next_week_count,
            next_month_count,
            event_types,
            neighborhoods_with_events,
            ROUND(COALESCE(avg_event_cost, 0), 2) as avg_event_cost,
            free_events_count,
            (total_events - free_events_count) as paid_events_count
        FROM EventCounts
        """

        try:
            params = (week_ahead, week_ahead, end_date, end_date)
            results = self.db.execute_query(query, params)

            if results:
                stats = results[0]
                return {
                    "days_ahead": days_ahead,
                    "total_events": stats["total_events"],
                    "time_breakdown": {
                        "next_week": stats["next_week_count"],
                        "next_month": stats["next_month_count"],
                        "later": stats["total_events"]
                        - stats["next_week_count"]
                        - stats["next_month_count"],
                    },
                    "event_diversity": {
                        "total_event_types": stats["event_types"],
                        "neighborhoods_with_events": stats["neighborhoods_with_events"],
                    },
                    "cost_analysis": {
                        "free_events": stats["free_events_count"],
                        "paid_events": stats["paid_events_count"],
                        "avg_cost": stats["avg_event_cost"],
                    },
                }
            else:
                return {
                    "days_ahead": days_ahead,
                    "total_events": 0,
                    "time_breakdown": {"next_week": 0, "next_month": 0, "later": 0},
                    "event_diversity": {
                        "total_event_types": 0,
                        "neighborhoods_with_events": 0,
                    },
                    "cost_analysis": {
                        "free_events": 0,
                        "paid_events": 0,
                        "avg_cost": 0,
                    },
                }

        except Exception as e:
            print(f"Error getting event stats: {e}")
            return {}

    def generate_comprehensive_azure_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report combining all Azure analytics.

        Returns:
            Complete Azure analytics report
        """
        report_timestamp = datetime.now()

        try:
            report = {
                "report_metadata": {
                    "generated_at": report_timestamp.isoformat(),
                    "report_type": "azure_database_analytics",
                    "data_source": "Azure SQL Database",
                },
                "user_growth": self.get_new_user_stats(),
                "content_creation": self.get_content_creation_stats(),
                "neighborhood_stats": self.get_neighborhood_stats(),
                "community_engagement": self.get_post_engagement_stats(),
                "event_stats": self.get_event_stats(),
                "summary": {
                    "report_generated": report_timestamp.isoformat(),
                    "data_categories": 5,
                },
            }

            return report

        except Exception as e:
            print(f"Error generating comprehensive Azure report: {e}")
            return {
                "error": str(e),
                "generated_at": report_timestamp.isoformat(),
                "status": "failed",
            }


# Global instance for easy importing
azure_analytics = AzureAnalytics()
