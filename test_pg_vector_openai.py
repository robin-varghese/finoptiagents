import openai
import json # To convert JSON objects to strings
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_KEY")

# Assuming you have your OpenAI API key set up as an environment variable
openai.api_key = OPENAI_KEY

def generate_combined_embedding(user_id: str, action: dict, result: dict) -> list[float]:
    """
    Generates a vector embedding from user_id, action, and result using OpenAI.
    """
    # 1. Concatenate the data into a single string
    # Convert JSON objects to compact strings for embedding
    action_str = json.dumps(action, separators=(',', ':'))
    result_str = json.dumps(result, separators=(',', ':'))

    combined_text = f"user_id: {user_id} action: {action_str} result: {result_str}"

    try:
        # 2. Send to an embedding model
        response = openai.embeddings.create(
            input=combined_text,
            model="text-embedding-ada-002" # Or your chosen embedding model
        )
        # 3. Receive the vector
        # The embedding is usually in response.data[0].embedding
        vector_value = response.data[0].embedding
        return vector_value
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None
"""
# --- Example Usage ---
if __name__ == "__main__":
    test_user_id = "user123"
    test_action = {"type": "login", "status": "success"}
    test_result = {"session_id": "abcde123", "timestamp": "2024-05-24T10:00:00Z"}

    embedding = generate_combined_embedding(test_user_id, test_action, test_result)

    if embedding:
        print(f"Generated embedding (first 5 elements): {embedding[:5]}...")
        print(f"Generated embedding (all elements): {embedding}")
        print(f"Embedding dimension: {len(embedding)}")
        # Now you would insert this 'embedding' into your 'vector_value' column
        # using your PostgreSQL client library (e.g., psycopg2 in Python)
        """