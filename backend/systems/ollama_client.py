import os
import re
import json
import requests


class OllamaClient:
    def __init__(self, host, model, timeout):
        self.host = host.rstrip("/")  # remove trailing slash if any
        self.model = model
        self.timeout = timeout

    def list_models(self):
        """Get a list of available models"""
        url = f"{self.host}/v1/models"
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def connect_to_model(self, model_name=None):
        """Connect to a specific model"""
        model_name = model_name or self.model
        url = f"{self.host}/v1/models/{model_name}"
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def generate_chat_completion(self, payload):
        """Generate a chat completion"""
        url = f"{self.host}/v1/chat/completions"
        try:
            # Ensure model is in payload if not present
            if "model" not in payload:
                payload["model"] = self.model

            # Check if streaming is requested
            stream = payload.get("stream", False)

            r = requests.post(url, json=payload, timeout=self.timeout, stream=stream)
            r.raise_for_status()

            if stream:
                return self._parse_streaming_response(r)
            else:
                return r.json()
        except requests.RequestException as e:
            return {"error": str(e)}

   
    def _parse_streaming_response(self, response):
        """Yields content chunks from a streaming response"""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]  # Strip "data: "
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass

    def post_process_json(self, format_type, output_file):
        # 6. JSON Post-Processing / Validation
        if format_type == "json":
            print("\n\n🔍 JSON Post-Processing Check...")
            try:
                # We read the cleaned file back
                with open(output_file, "r") as f:
                    data = json.load(f)

                print("✅ Success! Valid JSON parsed.")
                print(f"📊 Extracted Keys: {list(data.keys())}")
                if "cost" in data:
                    print(f"💰 Detected Cost: ${data['cost']}")

            except json.JSONDecodeError as e:
                print(f"❌ JSON Validation Failed: {e}")
                # Debug info
                with open(output_file, "r") as f:
                    print(f"File content was: {f.read()}")


def clean_json_block(text: str) -> str:
    """
    Cleans a JSON string from markdown code blocks if present.
    Example:
    ```json
    {"key": "value"}
    ```
    becomes {"key": "value"}
    """
    # Remove ```json or ``` at the start
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    # Remove ``` at the end
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# Example usage
if __name__ == "__main__":
    client = OllamaClient()
    models = client.list_models()
    print("Available models:", models)
    # models is object so you can parse it as needed
    for model in models.get("data", []):
        print(f"Model: - {model['id']}")

    model_info = client.connect_to_model()
