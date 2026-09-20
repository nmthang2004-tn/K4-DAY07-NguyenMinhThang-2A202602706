"""Checkpoint 6 benchmark: compare chunking strategies and metadata A/B tests.

Run from the project root with ``python bench.py``.  The output is deliberately
saved as a plain-text audit trail so its top-3 evidence can be copied to the
reports without re-running the experiment.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from src.chunking import FixedSizeChunker, HeadingChunker, SentenceChunker
from src.embeddings import _mock_embed
from src.models import Document
from src.store import EmbeddingStore


DATA_DIR = Path("data/ecommerce_policy")
OUTPUT_FILE = Path("ket_qua_benchmark.txt")

# ``answer_markers`` are content-level checks.  A document-id hit alone is not
# counted as an answer: the retrieved context must contain every marker.
QUERIES = [
    ("Q1", "Người bán phải phản hồi yêu cầu trả hàng trong bao nhiêu ngày?",
     "shopee_seller_dispute_response", None, ("3 ngày làm việc kể từ khi nhận được thông báo",)),
    ("Q2", "Khi giao hàng thực phẩm tươi sống bị khiếu nại, người bán phải phản hồi trong bao lâu?",
     "shopee_seller_dispute_response", {"audience": "seller"},
     ("Đơn hàng thực phẩm tươi sống & đông lạnh", "Phản hồi trong vòng 24 giờ")),
    ("Q3", "Người mua cần cung cấp gì khi yêu cầu trả hàng điện tử lỗi nhà sản xuất (DOA)?",
     "shopee_buyer_return_timeline", {"audience": "buyer"},
     ("30 ngày kể từ ngày nhận hàng", "Sản phẩm chưa qua sử dụng, còn nguyên seal và phụ kiện")),
    ("Q4", "Hậu quả của việc người bán không phản hồi khiếu nại đúng hạn là gì?",
     "shopee_seller_dispute_response", None,
     ("Shopee sẽ tự động chấp nhận yêu cầu Trả hàng/Hoàn tiền", "ảnh hưởng đến điểm đánh giá cửa hàng")),
    ("Q5", "Video bằng chứng đóng gói phải đáp ứng yêu cầu gì khi gửi cho Shopee?",
     "shopee_seller_evidence_guide", None,
     ("dung lượng không quá 100MB/video", "tối đa 1 phút", "Video: MP4, AVI")),
]


def load_documents() -> list[tuple[str, str, dict[str, str]]]:
    documents = []
    with (DATA_DIR / "sources.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            text = Path(row["file_path"]).read_text(encoding="utf-8")
            text = re.sub(r"\A---.*?---\s*", "", text, flags=re.DOTALL)
            documents.append((row["doc_id"], text, {
                "doc_id": row["doc_id"], "source_doc_id": row["doc_id"], "audience": row["audience"],
                "category": row["category"], "title": row["title"],
            }))
    return documents


def build_store(chunker, documents):
    store = EmbeddingStore(embedding_fn=_mock_embed)
    lengths, count = [], 0
    for source_id, text, metadata in documents:
        chunks = chunker.chunk(text)
        lengths.extend(map(len, chunks))
        store.add_documents([
            Document(id=f"{source_id}::chunk_{index}", content=chunk,
                     metadata={**metadata, "chunk_index": index})
            for index, chunk in enumerate(chunks)
        ])
        count += len(chunks)
    return store, count, sum(lengths) / count if count else 0.0


def is_gold(result, source_id: str) -> bool:
    return result["metadata"].get("source_doc_id") == source_id


def evaluate(results, source_id: str, markers: tuple[str, ...]) -> tuple[int, bool, bool]:
    gold_rank = next((rank for rank, row in enumerate(results, 1) if is_gold(row, source_id)), None)
    # Ignore Markdown emphasis so a source phrase such as ``**3 ngày**`` can
    # be checked against its plain-text gold marker, while retaining words and
    # numbers that make the marker answer-specific.
    context = re.sub(r"[*_`]+", "", "\n".join(row["content"].casefold() for row in results))
    context = re.sub(r"\s+", " ", context)
    answer_in_context = all(re.sub(r"\s+", " ", marker.casefold()) in context for marker in markers)
    # Required scale: 2 = gold top-1 + answer context; 1 = gold top-2/3;
    # 0 = no gold chunk, or context cannot answer the question.
    score = 2 if gold_rank == 1 and answer_in_context else 1 if gold_rank in (2, 3) and answer_in_context else 0
    return score, gold_rank is not None, answer_in_context


def render_results(lines, label, results):
    lines.append(f"    {label} top-3:")
    for rank, row in enumerate(results, 1):
        preview = " ".join(row["content"].split())[:150]
        lines.append(
            f"      #{rank} score={row['score']:+.4f} "
            f"source={row['metadata'].get('source_doc_id')} "
            f"chunk={row['metadata'].get('chunk_index')} | {preview}"
        )


def main() -> None:
    # PowerShell sessions configured with a legacy code page otherwise fail
    # while printing the Vietnamese benchmark evidence.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    documents = load_documents()
    strategies = {
        "FixedSize(500, overlap=50)": FixedSizeChunker(500, 50),
        "SentenceChunker(max_sentences=3)": SentenceChunker(3),
        "HeadingChunker(chunk_size=500, levels=1-3)": HeadingChunker(chunk_size=500),
    }
    lines = [
        "CHECKPOINT 6 — BENCHMARK RETRIEVAL", "Embedding backend: MockEmbedder (MD5 deterministic; not semantic)",
        "Content score requires ALL answer markers in the retrieved top-3 context.",
        f"Documents: {len(documents)}", "",
    ]
    for name, chunker in strategies.items():
        store, count, avg_length = build_store(chunker, documents)
        total = 0
        lines.extend([f"=== {name} ===", f"chunks={count}; avg_length={avg_length:.1f} characters"])
        for qid, query, gold_doc, metadata_filter, markers in QUERIES:
            unfiltered = store.search(query, top_k=3)
            # Q2/Q3 must expose both sides of the A/B experiment.
            filtered = store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter) if metadata_filter else None
            scored_results = filtered if filtered is not None else unfiltered
            score, doc_hit, answer_in_context = evaluate(scored_results, gold_doc, markers)
            total += score
            lines.append(f"\n[{qid}] {query}")
            render_results(lines, "unfiltered", unfiltered)
            if filtered is not None:
                render_results(lines, f"filtered {metadata_filter}", filtered)
            lines.append(f"    evaluation (used {'filtered' if filtered is not None else 'unfiltered'}): "
                         f"gold_doc_in_top3={doc_hit}; answer_in_context={answer_in_context}; score={score}/2")
        lines.extend([f"Strategy score: {total}/10", ""])
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
