# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Minh Thắng
**Nhóm:** 2A202602420
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity cao (gần 1.0) nghĩa là hai vector hướng gần nhau trong không gian nhiều chiều — tức hai đoạn văn bản có **ý nghĩa/ngữ cảnh tương tự nhau**, dù dùng từ vựng khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Con mèo đang ngồi trên bậc thềm."
- Câu B: "The cat is resting on the doorstep."
- Tại sao tương đồng: Cả hai cùng mô tả một con mèo đang nghỉ trên bậc cửa — cùng hành động, cùng đối tượng, cùng vị trí, dù ngôn ngữ hoàn toàn khác. Embedding model đã học được biểu diễn semantic (ngữ nghĩa), không đơn thuần đếm từ trùng nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Tôi thích ăn pizza."
- Câu B: "Chiếc xe hơi màu đỏ chạy rất nhanh."
- Tại sao khác: Không có từ chung, chủ đề hoàn toàn khác nhau (đồ ăn vs phương tiện), nên embedding sẽ nằm ở hai vùng không gian rất xa nhau.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Vì embedding vector có thể có magnitude khác nhau (văn dài vs. văn ngắn) nhưng vẫn cùng hướng/ý nghĩa. Cosine chỉ đo góc giữa hai vector (hướng), bỏ qua độ lớn, nên phù hợp với semantic similarity. Euclid đo khoảng cách tuyệt đối nên nhạy cảm với độ dài văn bản — một đoạn dài gấp đôi sẽ "xa" hơn dù nội dung tương tự.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: `ceil((độ_dài − overlap) / (chunk_size − overlap))`
> `ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23 chunks`
>
> Kiểm tra bằng FixedSizeChunker:
> ```
> python -c "from src.chunking import FixedSizeChunker; print(len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)))"
> → 23 ✓
> ```
>
> **Đáp án: 23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với overlap=100: `ceil((10000 − 100) / (500 − 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks` (tăng từ 23 lên 25).
> Overlap lớn hơn giúp **giữ nguyên ngữ cảnh ở vùng ranh giới** — câu hoặc đoạn bị cắt ngang sẽ không mất thông tin hoàn toàn. Nhược điểm là tốn thêm chunk (tăng chi phí lưu trữ và search), nên cần cân bằng giữa chất lượng retrieval và hiệu suất.

---


## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

> Sử dụng biểu thức chính quy (regex) để tách câu dựa trên các ký tự kết thúc câu `[.!?]` kết hợp với khoảng trắng. Thuật toán duyệt qua danh sách câu đã tách và gom tối đa `max_sentences` câu vào mỗi chunk trước khi chuyển sang chunk tiếp theo. Xử lý các trường hợp ngoại lệ (edge cases) như chuỗi rỗng hoặc văn bản chỉ chứa khoảng trắng bằng cách trả về danh sách rỗng, đồng thời loại bỏ khoảng trắng thừa ở đầu và cuối mỗi câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Triển khai thuật toán chia nhỏ văn bản theo cơ chế đệ quy, lần lượt thử các separator theo thứ tự ưu tiên giảm dần: đoạn văn (`\n\n`), dòng (`\n`), từ (` `) và từng ký tự (`""`). Trường hợp cơ sở (base case) xảy ra khi độ dài văn bản nhỏ hơn hoặc bằng `chunk_size`, hoặc khi đã duyệt hết danh sách separator thì chuyển sang cắt cứng theo ký tự. Các đoạn văn bản sau khi phân tách được gom lại thành các chunk có độ dài không vượt quá giới hạn `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

> Triển khai kho lưu trữ dạng in-memory bằng danh sách các dictionary record, trong đó mỗi record chứa nội dung chunk, vector embedding và metadata. Hàm `_make_record` thực hiện deep-copy metadata và bổ sung khóa `doc_id` để truy vết tài liệu gốc. Khi tìm kiếm, hàm `_search_records` tính cosine similarity giữa query embedding và từng vector tài liệu, sắp xếp kết quả theo điểm tương tự giảm dần, lấy `top_k` kết quả và loại bỏ vector embedding 1536 chiều khỏi dữ liệu trả về.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

> Áp dụng cơ chế lọc trước (Pre-filtering): lọc danh sách record theo `metadata_filter` trước khi tính cosine similarity và lựa chọn `top_k` kết quả phù hợp nhất. Cách tiếp cận này tránh trường hợp các tài liệu không thỏa mãn điều kiện chiếm vị trí trong `top_k` nếu thực hiện lọc sau (Post-filtering). Đối với `delete_document`, hệ thống duyệt danh sách in-memory và loại bỏ toàn bộ chunk có `metadata['doc_id']` trùng với ID cần xóa, trả về `True` nếu có ít nhất một chunk bị xóa và `False` nếu không tìm thấy tài liệu.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

> Đầu tiên, agent kiểm tra cơ sở tri thức; nếu kho rỗng hoặc không tìm thấy chunk liên quan, hệ thống trả về thông báo không tìm thấy thông tin mà không gọi LLM nhằm tiết kiệm token. Khi có dữ liệu phù hợp, agent truy xuất `top_k` chunk, định dạng ngữ cảnh theo số thứ tự `[1]`, `[2]`,... kèm nguồn tài liệu và đưa vào system prompt. Prompt được thiết kế với ràng buộc chỉ trả lời dựa trên ngữ cảnh được cung cấp và yêu cầu trích dẫn nguồn theo định dạng `[n]`, giúp đảm bảo tính truy vết nguồn thông tin (Source Traceability).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```plaintext
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\DayVinAI\Day7\K4-DAY07-NguyenMinhThang-2A202602706
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================== 42 passed in 0.11s ==============================
```

**Số lượng bài test vượt qua (pass): 42 / 42 (100%)**

**Tự đánh giá: Hoàn thiện code (Core Implementation — tests): 30 / 30 điểm.**

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | | | cao / thấp | | |
| 2 | | | cao / thấp | | |
| 3 | | | cao / thấp | | |
| 4 | | | cao / thấp | | |
| 5 | | | cao / thấp | | |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> *Viết 2-3 câu:*

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Người bán phải phản hồi yêu cầu trả hàng trong bao nhiêu ngày? | `shopee_buyer_return_condition`, chunk 12 (hoàn Xu) | +0.2550 | Không: gold document ở top-2 nhưng context thiếu câu trả lời hoàn chỉnh | Không trả lời; context không đủ căn cứ |
| 2 | Thực phẩm tươi sống bị khiếu nại, người bán phản hồi bao lâu? *(filter=seller)* | `shopee_seller_dispute_response`, chunk 4 (quy trình 3 ngày) | +0.0888 | Không: gold doc top-1 nhưng sai section, không có “thực phẩm tươi sống: 24 giờ” | Không trả lời; context không đủ căn cứ cho 24 giờ |
| 3 | Người mua cần cung cấp gì khi trả hàng điện tử DOA? *(filter=buyer)* | `shopee_buyer_non_returnable`, chunk 2 (danh mục hạn chế) | +0.3120 | Không: không có tài liệu/section DOA trong top-3 | Không trả lời; context không đủ căn cứ |
| 4 | Hậu quả khi người bán không phản hồi đúng hạn? | `shopee_seller_evidence_guide`, chunk 1 (bằng chứng giao hàng) | +0.2785 | Không: không có `shopee_seller_dispute_response` trong top-3 | Không trả lời; context không đủ căn cứ |
| 5 | Video bằng chứng đóng gói phải đáp ứng gì? | `shopee_buyer_refund_timeline`, chunk 7 (hoàn tiền SPayLater) | +0.2537 | Không: không có tài liệu/section yêu cầu video trong top-3 | Không trả lời; context không đủ căn cứ |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **0 / 5**

### Thiết lập và cách chấm

- Chiến lược cá nhân ghi trong bảng trên: `FixedSizeChunker(chunk_size=500, overlap=50)`; 46 chunks, độ dài trung bình 466.9 ký tự. Overlap giữ một phần ngữ cảnh ở ranh giới nhưng chunk vẫn có thể bắt đầu/kết thúc giữa câu hoặc section.
- Backend: **MockEmbedder** (MD5, 64 chiều). Tôi đã thử backend local nhưng `sentence-transformers` không khởi tạo được vì môi trường có PyTorch 2.3.0, trong khi gói hiện tại yêu cầu từ 2.4. Do đó score cosine chỉ dùng để tái lập thứ hạng, **không** được diễn giải là độ gần ngữ nghĩa.
- Mỗi câu khai báo các marker đặc trưng phải xuất hiện trong toàn bộ context top-3 (ví dụ Q5: “dung lượng không quá 100MB/video”, “tối đa 1 phút”, “Video: MP4, AVI”). Chỉ trùng `doc_id` không đủ. Điểm nội dung: 2 nếu top-1 gold và đủ marker; 1 nếu top-2/3 gold và đủ marker; 0 nếu thiếu context trả lời được.
- Kết quả nội dung FixedSizeChunker: Q1=0, Q2=0, Q3=0, Q4=0, Q5=0, tổng **0/10**. Vì không cấu hình LLM trong lần đo, cột “Agent” là câu trả lời có thể grounding trực tiếp từ context; các dòng “không trả lời” không được suy diễn từ ngoài context.

### A/B metadata filter (Q2 và Q3)

| Chiến lược | Q2 không filter → filter `seller` | Q3 không filter → filter `buyer` | Kết luận |
|---|---|---|---|
| FixedSize(500, overlap=50) | Không có gold doc → có gold doc nhưng thiếu câu 24 giờ | Không có gold doc → không có gold doc | Filter tăng document recall cho Q2 nhưng chưa đưa đúng section vào top-3. |
| SentenceChunker(3) | Không có gold doc → có gold doc nhưng thiếu câu 24 giờ | Gold/top-1 đúng → kết quả top-1 vẫn đúng | Q2 có lợi một phần; Q3 không thực sự cần filter trong lần đo này. |
| HeadingChunker(500) | Gold doc ở top-2 → gold doc ở top-1, nhưng đều sai section | Không có gold doc → không có gold doc | Kết quả của R3 (Vàng); filter cải thiện rank tài liệu Q2, song không đủ để trả lời. |

Top-3 đầy đủ, score, count và avg_length của cả ba chiến lược nằm trong `ket_qua_benchmark.txt`.

### Failure case thật và đề xuất sửa

**Q2 hỏng:** Sau filter `audience=seller`, top-1 của FixedSize là `shopee_seller_dispute_response` nhưng chunk được trả về là đoạn quy trình có “3 ngày”, không phải section trường hợp đặc biệt có “24 giờ”. Đây là minh chứng rằng chấm chỉ theo `doc_id` sẽ báo hit sai: document đúng nhưng context không thể trả lời.

Nguyên nhân trực tiếp là MockEmbedder băm toàn bộ chuỗi, nên không mã hoá quan hệ giữa “thực phẩm tươi sống” và section trường hợp đặc biệt; FixedSize cũng có thể cắt rời section. Cách sửa ưu tiên là dùng multilingual semantic embedder sau khi đồng bộ PyTorch; đồng thời nhóm có thể đối chiếu với HeadingChunker của R3 để giữ tiêu đề section làm ngữ cảnh.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Không nên coi “gold document nằm trong top-3” là câu trả lời đúng: một tài liệu chính sách có nhiều section gần chủ đề nhưng chỉ một section chứa con số cần hỏi. Metadata filter nên được kiểm chứng bằng A/B; ở Q2 nó loại được buyer corpus nhưng vẫn không lấy được câu 24 giờ, còn Q3 gần như không đổi nên query này chưa chứng minh được lợi ích của filter.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | / 5 |
| Hướng tiếp cận của tôi (My Approach) | / 10 |
| Hoàn thiện code (Core Implementation — tests) | / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | / 5 |
| Kết quả truy xuất của tôi (Competition Results) | / 10 |
| **Tổng phần cá nhân** | **/ 60** |
