import openai
import json


def call_gpt(prompt, model="gpt-4o"):
    openai.api_key = 'sk-proj-zvfr2IvWfqEUqsnmwIBJT3BlbkFJMxh6YiSgfcG6vEcMGJ35'
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        print("inside:", response['choices'][0]['message']['content'])
        return response['choices'][0]['message']['content']
    except Exception as e:
        print("GPT Error: ", e)
        return None


def parse_suggestion(gpt_output):
    try:
        return json.loads(gpt_output)
    except json.JSONDecodeError:
        print("Failed to parse GPT output.")
        return {}





