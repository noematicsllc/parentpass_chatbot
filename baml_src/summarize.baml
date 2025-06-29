function SummarizeAnalyticsQuery(
  query_name: string,
  query_description: string, 
  raw_data: string,
  data_type: string
) -> string {
  client Custom41Mini
  prompt #"
    You are preparing analytics data for a chatbot that will answer administrator questions about ParentPass app performance.
    
    Query Name: {{ query_name }}
    Query Description: {{ query_description }}
    Data Type: {{ data_type }}
    
    Raw Data: {{ raw_data }}
    
    Your task is to organize key analytics data comprehensively so a chatbot can answer administrator questions about performance and trends.
    
    Requirements:
    1. **Include key metrics and totals** - Aggregate numbers, counts, percentages, averages
    2. **Structure for searchability** - Organize so a chatbot can quickly find specific metrics
    3. **Add context labels** - Label each metric clearly (e.g., "time period: last 7 days")
    4. **Include metadata** - Time ranges, data collection methods, row counts, etc.
    5. **Focus on summaries** - Show totals, averages, and high-level breakdowns rather than individual records
    6. **List all categories** - Show all sections, user types, time periods, etc. with their summary metrics
    
    Structure your response as:
    ## {{ query_name }}
    
    ### Query Details
    - Description: {{ query_description }}
    - Data Period: [extract from data]
    - Total Records: [count if available]
    - Data Source: [BigQuery/Azure SQL]
    
    ### Complete Metrics
    [Organize key totals, averages, and summary statistics with clear labels]
    
    ### Summary Breakdown
    [Show category totals, time period summaries, and high-level patterns - NO individual record samples]
    
    ### Technical Details
    [Any parameters, filters, or methodology notes]
    
    IMPORTANT: Do NOT include individual record samples or detailed timestamp entries. Focus on aggregated metrics, totals, and high-level breakdowns that provide insights without overwhelming detail.
  "#
} 