from dotenv import load_dotenv

load_dotenv()

from app.agents.indexer.graph import graph  # noqa: E402

json_path = (
    r"C:\Users\gfdsfgdsfg\Desktop\takeout-20260608T043452Z-3-001"
    r"\Takeout\YouTube 및 YouTube Music\시청 기록\시청 기록.json"
)

result = graph.invoke(
    {
        "json_path": json_path,
        "raw_data": [],
        "cleaned_data": [],
        "error": None,
        "saved_count": None,
    }
)

print(f"전처리 후: {len(result['cleaned_data'])}개")
print(f"저장된 개수: {result['saved_count']}개")
print(f"에러: {result['error']}")
