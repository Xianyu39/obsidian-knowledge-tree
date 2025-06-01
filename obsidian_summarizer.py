import httpx
import argparse
import os
import openai
import dotenv
from typing import Optional, List

dotenv.load_dotenv()

OB_API_BASE_URL = os.getenv("OB_API_BASE_URL", "http://127.0.0.1:27123")
OB_API_KEY = os.getenv("OB_API_KEY")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://api.openai.com")
LLM_API_KEY = os.getenv("LLM_API_KEY")

if OB_API_BASE_URL:
    print(f"Using Obsidian API base URL: {OB_API_BASE_URL}")
else:
     print("Obsidian API base URL not set. Using default: http://127.0.0.1:27123")
if OB_API_KEY:
    print(f"Using Obsidian API key: {OB_API_KEY}")
else:
    print("Obsidian API key not set. Ensure you have the correct key for authentication.")
if LLM_API_BASE_URL: 
    print(f"Using LLM API base URL: {LLM_API_BASE_URL}")
else:
    print("LLM API base URL not set. Using default: https://api.openai.com")
if LLM_API_KEY: 
    print(f"Using LLM API key: {LLM_API_KEY}")
else:
    print("LLM API key not set. Ensure you have the correct key for authentication.")

with open("system_prompt_template.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT_TEMPLATE = f.read()
DV_QUERY = """TABLE FROM {tag} SORT creation DESC"""


def get_docs_by_tag(tag: str):
    headers = {
        "Authorization": f"Bearer {OB_API_KEY}",
        "Content-Type": "application/vnd.olrapi.dataview.dql+txt",
    }
    payload = DV_QUERY.format(tag=tag)
    response = httpx.post(
        f"{OB_API_BASE_URL}/search/",
        headers=headers,
        data=payload
    )
    filenames = [item["filename"] for item in response.json()]
    
    headers = {
        "Authorization": f"Bearer {OB_API_KEY}",
        "accept": "text/markdown",
    }
    contents = []
    for filename in filenames:
        response = httpx.get(f"{OB_API_BASE_URL}/vault/{filename}", headers=headers)
        response.raise_for_status()
        contents.append(response.text)
        
    return filenames, contents

def summarize_docs(docs: List[str], docs_titles: List[str], model: str, base_url: str, api_key: str, output_file: str) -> None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
    }
    joined_docs = ""
    for i, (title, doc) in enumerate(zip(docs_titles, docs)):
        joined_docs += f"Note {i+1}: {title}\n{doc}\n\n"
    
    client = openai.Client(
        base_url=f"{base_url}/v1/",
        api_key=api_key
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE},
            {"role": "user", "content": f"Please summarize the following text:\n{joined_docs}"}
        ],
        stream=True,
        max_tokens=4096,
        temperature=0.7,
    )
    
    collected_chunks = []
    with open(output_file, "w", encoding="utf-8", ) as f:
        for chunk in response:
            token=chunk.choices[0].delta.content
            if token:
                collected_chunks.append(token)
                f.write(token)
                f.flush()
                print(token, end="", flush=True)
                
def main():
    parser = argparse.ArgumentParser(description="Summarize Obsidian notes by tag.")
    parser.add_argument("--tag", type=str, help="Tag to filter notes by")
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo", help="Model to use for summarization")
    parser.add_argument("--output", type=str, default="summary.md", help="Output file for the summary")
    args = parser.parse_args()
    
    titles, docs = get_docs_by_tag(args.tag)
    if not docs:
        print(f"No documents found with tag '{args.tag}'.")
        return
    print(f"Found {len(docs)} documents with tag '{args.tag}'. Summarizing...")
    summarize_docs(docs, titles, args.model, LLM_API_BASE_URL, LLM_API_KEY, args.output)
    print(f"\nSummary written to {args.output}")
    
if __name__ == "__main__":
    main()
    

"""

"""