from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        # Step 1: Retrieve top-k chunks
        results = self._store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."

        # Step 2: Build context with numbered citations [1] [2] [3]
        context_lines = []
        for i, r in enumerate(results, 1):
            doc_id = r["metadata"].get("doc_id", "unknown")
            content = r["content"]
            context_lines.append(f"[{i}] (Nguồn: {doc_id}) {content}")

        context = "\n\n".join(context_lines)

        # Step 3: Build prompt — cite [n] in answer, only use provided context
        prompt = (
            "Bạn là trợ lý hỏi đáp dựa trên ngữ cảnh được cung cấp.\n"
            "CHỈ trả lời dựa trên ngữ cảnh bên dưới. Nếu không có thông tin, hãy nói rõ.\n"
            "Khi trả lời, hãy trích dẫn số [n] tương ứng với nguồn.\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n\n"
            "Câu trả lời (có trích dẫn nguồn):"
        )

        return self._llm_fn(prompt)
