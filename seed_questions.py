import sys
from llm.redis_client import add_question, clear_questions


def main():
    if len(sys.argv) != 2:
        print("Usage: python seed_questions.py <questions.txt>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines()]
    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(1)

    clear_questions()
    count = 0
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        add_question(ln)
        count += 1

    print(f"Seeded {count} questions from {path}")


if __name__ == "__main__":
    main()
