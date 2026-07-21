from pathlib import Path

KNOWLEDGE_BASE_PATH = Path("knowledge_base")


def load_markdown_files():
    """
    Load all markdown files from the knowledge_base folder.

    Returns:
        list of dictionaries containing:
        - filename
        - content
    """

    documents = []

    for file_path in KNOWLEDGE_BASE_PATH.glob("*.md"):

        with open(file_path, "r", encoding="utf-8") as file:

            documents.append(
                {
                    "filename": file_path.name,
                    "content": file.read()
                }
            )

    return documents