class Message {
  role "user" | "assistant"
  content string
}

class State {
  recent_messages Message[]
}

class AnalyticsQuestion {
  category AnalyticsCategory
  question string @description("The question the user is asking about the analytics")
}

enum AnalyticsCategory {
  CONTENT @description("Questions about posts, activities, freebies, content creation, what content is available")
  EVENTS @description("Questions about upcoming events, activities, scheduled events, event participation")
  REGISTRATIONS @description("Questions about new users, user growth, sign-ups, user acquisition trends")
  NEIGHBORHOODS @description("Questions about geographic distribution, neighborhoods, community locations")
  ENGAGEMENT @description("Questions about user activity, time spent, session data, app usage, push notifications, search behavior")
  USERS @description("Questions about active users, daily/weekly/monthly active users, user behavior patterns")
}

// function DetermineAnalyticsCategory(user_question: string) -> AnalyticsCategory {
//   client Custom41Mini
//   prompt #"
//     You need to determine what type of analytics data is required to answer a user's question about the ParentPass application.

//     User question: {{ user_question }}

//     Based on the question, determine which analytics type is most relevant:

//     - CONTENT: Questions about posts, activities, freebies, content creation, what content is available
//     - EVENTS: Questions about upcoming events, activities, scheduled events, event participation
//     - REGISTRATIONS: Questions about new users, user growth, sign-ups, user acquisition trends
//     - NEIGHBORHOODS: Questions about geographic distribution, neighborhoods, community locations
//     - ENGAGEMENT: Questions about user activity, time spent, session data, app usage, push notifications, search behavior
//     - USERS: Questions about active users, daily/weekly/monthly active users, user behavior patterns

//     Examples:
//     - "How many new users signed up this month?" → REGISTRATIONS
//     - "What events are coming up?" → EVENTS  
//     - "How engaged are our users?" → ENGAGEMENT
//     - "What content has been created recently?" → CONTENT
//     - "Which neighborhoods are most active?" → NEIGHBORHOODS
//     - "How many daily active users do we have?" → USERS

//     {{ ctx.output_format }}
//   "#
// }

function AnswerAnalyticsQuestion(state: State, analytics_data: string) -> Message {
  client Custom41Mini
  prompt #"
    You are a helpful assistant for administrators of the ParentPass application.
    You can answer questions about the site content and analytics.
    
    You will be given a report of the latest analytics data. Use this data to answer questions about the site content and analytics. Summarize the data and answer the user's questions to the best of your ability.

    Emphasize important data points with ==highlight==. Include what the number refers to. For example, say "==100 new users== this month" instead of "==100== new users this month".
    You may offer insights about the data, but don't make up data that is not in the analytics. Accuracy is important.

    If you can't answer the question with the provided data, simply say "I don't have that information." Don't make up information.

    Analytics data:
    {{ analytics_data }}

    Current state: {{ state.recent_messages }}

    {{ ctx.output_format }}
  "#
}

function Chat(state: State) -> Message | AnalyticsQuestion {
  client Custom41Mini
  prompt #"
    You are a helpful assistant for administrators of the ParentPass application.
    You are here to answer questions about the site content and analytics.
    
    As an assistant for the ParentPass application, you are only allowed to answer questions about the
    ParentPass application. You are not allowed to answer questions about other applications, or about the
    world at large. You will try to be helpful and informative if the question is related to content found 
    in the ParentPass application, but refuse if the conversation drifts too far off topic. Politely remind 
    the user that your job is to help with ParentPass, and that you are not able to answer questions about 
    other applications or the world at large.

    You will be given a list of analytics categories. You will need to determine which category is most
    relevant to the user's question.

    Current state: {{ state.recent_messages }}

    {{ ctx.output_format }}
  "#
}

function SummarizeMessages(messages: Message[]) -> string {
  client Custom41Mini
  prompt #"
    You are a helpful chatbot having a conversation with the user.
    That conversation can get long, and you need to summarize it to
    prevent your context from getting too long. Keep only the information
    you expect to need for followup questions.

    Content:
    {{ messages }}

  "#
}