import re


def chunk_markdown(document):
    """
    Split one markdown document into chunks based on ## headings.

    Args:
        document: {
            "filename": "...",
            "content": "..."
        }

    Returns:
        List of chunks.
    """

    filename = document["filename"]
    content = document["content"]

    # Split on ## headings
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)

    chunks = []

    # Skip the first section because it's before the first ##
    for section in sections[1:]:

        lines = section.strip().split("\n")

        heading = lines[0].strip()

        body = "\n".join(lines[1:]).strip()

        chunks.append(
    {
        "id": f"{filename}:{heading}",
        "source": filename,
        "heading": heading,
        "content": body
    }
)

    return chunks


def chunk_all_documents(documents):

    all_chunks = []

    for document in documents:

        all_chunks.extend(chunk_markdown(document))

    return all_chunks