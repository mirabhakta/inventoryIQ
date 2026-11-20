from utils.trend import compute_trend
import os
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Load environment variables
load_dotenv()

def get_gemini_client():
    """Create the Gemini client only when a key is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        return None, "GEMINI_API_KEY is not set."
        
    if genai is None:
        return None, "google-genai is not installed."
        
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash"), None

# -------------------------------
# 1. BUILD AI PAYLOAD
# -------------------------------

def build_payload(trend, model_name, accuracy, alerts_df, top_product=None, top_category=None):
    """
    Andrew Garcia Leopold: build the exact payload shape the API expects.
    This keeps the dashboard connected to Sarah's Gemini summary function.
    """
    top_alerts = []

    # Andrew Garcia Leopold: only send the top few alerts so the AI prompt stays short.
    if alerts_df is not None and not alerts_df.empty:
        sorted_alerts = alerts_df.sort_values(by="severity", ascending=False).head(3)

        for _, row in sorted_alerts.iterrows():
            top_alerts.append({
                "product": row.get("product", row.get("product_name", "Unknown")),
                "type": row.get("alert_type", "Unknown"),
                "severity": row.get("severity", 0),
            })

    return {
        "model": model_name,
        "accuracy": accuracy,
        "trend": trend,
        "top_alerts": top_alerts,
    }


def build_ai_payload(df):
    """
    Build structured payload for AI consumption.
    """
    if df.empty:
        return {"error": "No data available"}

    trend = compute_trend(df)

    payload = {
        "trend": trend,
        "latest_sales": float(df["sales"].iloc[-1]),
        "avg_sales": float(df["sales"].mean()),
        "max_sales": float(df["sales"].max()),
        "min_sales": float(df["sales"].min()),
        "data_points": len(df),
        "top_product": top_product,
        "top_category": top_category,
    }


# -------------------------------
# 2. GENERATE SUMMARY (TEAM PART)
# -------------------------------
def generate_summary(payload):
    """
    Sends structured payload to Gemini and returns summary text
    """
    try:
        client, client_error = get_gemini_client()
        if client_error:
            return {
                "status": "error",
                "message": client_error
            }

        # Andrew Garcia Leopold: support both the newer dashboard payload and
        # Sarah's older local-test payload so either path works without crashing.
        trend = payload.get("trend", "Unknown")
        accuracy = payload.get("accuracy", "not available")
        top_alerts = payload.get("top_alerts", [])
        top_product = payload.get("top_product", "Unknown")
        top_category = payload.get("top_category", "Unknown")

        prompt = f"""
You are a retail analytics assistant.

Model accuracy: {accuracy}
Sales trend: {trend}
Top alerts: {top_alerts}
Top product: {top_product}
Top category: {top_category}

Write a short, clear business summary (2-3 sentences):
- describe the current sales trend
- explicitly mention the top-performing product
- mention whether alerts are present or not
- suggest a simple next step

If a top product is provided, include it naturally in the summary.

Use plain, direct language suitable for a store manager. Avoid repeating raw metric values unless necessary.
        """

        response = client.generate_content(prompt)


        return {
            "status": "success",
            "text": response.text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Gemini is temporarily unavailable due to high demand. Please try again in a moment."
        }
