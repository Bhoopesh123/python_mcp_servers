import os
import openlit
from google import genai

# ==============================
# Initialize OpenLIT (Observability)
# ==============================
# OpenLIT automatically instruments the 'google' provider
openlit.init()

# ==============================
# Initialize Gemini Client
# ==============================
# The client automatically picks up 'GEMINI_API_KEY' from env vars
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ==============================
# Model Router
# ==============================
def route_query(message: str) -> str:
    """Select modern Gemini model based on query complexity."""
    words = len(message.split())

    if words < 20:
        # Ultra fast & budget friendly
        return "gemini-2.5-flash-lite" 
    elif words < 100:
        # Standard balanced model
        return "gemini-2.5-flash"
    else:
        # High-reasoning model for complex tasks
        return "gemini-3.1-pro-preview" 

# ==============================
# Model Caller
# ==============================
def call_model(model_id: str, message: str) -> str:
    """Call the Gemini API with the selected model."""
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=message
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Error with {model_id}: {e}")
        return fallback_model(message)

# ==============================
# Fallback Logic
# ==============================
def fallback_model(message: str) -> str:
    """Fallback to the most reliable lightweight model."""
    try:
        # Using a stable legacy-safe version
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message
        )
        return response.text
    except Exception as e:
        return f"❌ All models failed: {str(e)}"

# ==============================
# Main Chat Function with Evals
# ==============================
def chat(user_message: str) -> str:
    # 1. Route to best model
    model_to_use = route_query(user_message)

    # 2. Generate Answer
    answer = call_model(model_to_use, user_message)

    # 3. Hallucination Evaluation (OpenLIT)
    # Note: 'google' is the provider string for Gemini in OpenLIT
    try:
        evaluator = openlit.evals.Hallucination(
            provider="google", 
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Measure based on a dummy context (or your actual RAG context)
        evaluator.measure(
            prompt=user_message,
            contexts=["System knowledge base and real-time web search"],
            text=answer
        )
    except Exception as e:
        print(f"⚠️ Eval error: {e}")

    # 4. Content Guardrails
    try:
        guard = openlit.guard.All(
            provider="google",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        guard.detect(text=answer)
    except Exception as e:
        print(f"⚠️ Guardrail alert: {e}")

    return answer

# ==============================
# Execution Entry Point
# ==============================
if __name__ == "__main__":
    print("--- Gemini AI Assistant (v2026) ---")
    while True:
        user_input = input("\nAsk something (type 'exit' to quit): ")

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if not user_input.strip():
            continue

        result = chat(user_input)
        print(f"\n🤖 [{route_query(user_input)}] Answer:\n{result}")
