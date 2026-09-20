# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** 2A202602420
**Thành viên:** Nguyễn Minh Thắng — 2A202602706 · Nguyễn Thị Vàng — 2A202602897 · Nguyễn Minh Tuấn — 2A202602420
**Ngày:** 2026-09-20

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, bảo hành và quy định người bán/người mua trên sàn thương mại điện tử Shopee (Việt Nam)

**Tại sao nhóm chọn chủ đề này?**
> Shopee là sàn thương mại điện tử lớn nhất Việt Nam với lượng người dùng đông đảo, nhu cầu khiếu nại đổi trả rất phổ biến. Chính sách đổi trả của Shopee có cấu trúc phân loại rõ ràng (theo audience: buyer/seller), con số cụ thể (thời hạn ngày, phí hoàn tiền), và nhiều ngoại lệ — rất phù hợp để đánh giá retrieval với metadata filter và chunking strategy khác nhau.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Thời hạn yêu cầu Trả hàng Hoàn tiền cho Người mua | https://help.shopee.vn/portal/4/article/79180 | 2026-09-20 / not-stated | ~2,241 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 2 | Điều kiện chấp nhận yêu cầu Trả hàng cho Người mua | https://help.shopee.vn/portal/4/article/79140 | 2026-09-20 / not-stated | ~5,790 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 3 | Thời gian nhận tiền hoàn và cách kiểm tra tiền hoàn | https://help.shopee.vn/portal/4/article/79180 | 2026-09-20 / not-stated | ~4,058 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 4 | Danh mục sản phẩm không hỗ trợ trả hàng hoàn tiền | https://help.shopee.vn/portal/4/article/79244 | 2026-09-20 / not-stated | ~1,675 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 5 | Chính sách bảo hành thiết bị điện tử trên Shopee | https://help.shopee.vn/portal/4/article/79250 | 2026-09-20 / not-stated | ~2,117 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 6 | Thời gian Người bán phản hồi khiếu nại Trả hàng | https://banhang.shopee.vn/edu/article/1823 | 2026-09-20 / not-stated | ~2,670 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |
| 7 | Hướng dẫn cung cấp bằng chứng khiếu nại cho Người bán | https://banhang.shopee.vn/edu/article/1824 | 2026-09-20 / not-stated | ~3,000 | doc_id, title, source_url, retrieved_at, document_version, audience, category, language |

**Tổng số tài liệu:** 7 | **Tổng số ký tự:** ~21,551

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `shopee_buyer_return_timeline` | Định danh duy nhất mỗi tài liệu, dùng để truy xuất nhanh và debug |
| `title` | string | `Thời hạn yêu cầu Trả hàng Hoàn tiền cho Người mua` | Hiển thị kết quả trả về cho người dùng |
| `source_url` | string | `https://help.shopee.vn/...` | Dùng để trích nguồn khi trả lời, tăng độ tin cậy |
| `retrieved_at` | date | `2026-09-20` | Xác định độ mới của dữ liệu |
| `document_version` | string | `not-stated` | Biết nguồn có ghi rõ phiên bản hay không |
| `audience` | enum | `buyer` \| `seller` | **Lọc quan trọng nhất** — cho phép trả lời riêng cho người mua hoặc người bán |
| `category` | string | `chinh-sach-doi-tra` | Phân loại chủ đề, hỗ trợ lọc theo loại chính sách |
| `language` | string | `vi` | Dùng khi mở rộng corpus đa ngôn ngữ |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| `shopee_buyer_return_timeline` | FixedSizeChunker (300, overlap=0) | 8 | 280.1 | ❌ Có thể cắt giữa câu |
| `shopee_buyer_return_timeline` | SentenceChunker (3 câu) | 7 | 318.9 | ✅ Giữ nguyên câu |
| `shopee_buyer_return_timeline` | RecursiveChunker (300) | 10 | 222.2 | ✅ Giữ đoạn/từ |
| `shopee_buyer_return_timeline` | HeadingChunker (300) | 12 | 191.1 | ✅ Heading trên từng mảnh |
| `shopee_seller_dispute_response` | FixedSizeChunker (300, overlap=0) | 9 | 296.7 | ❌ |
| `shopee_seller_dispute_response` | SentenceChunker (3 câu) | 7 | 379.9 | ✅ |
| `shopee_seller_dispute_response` | RecursiveChunker (300) | 11 | 240.8 | ✅ |
| `shopee_seller_dispute_response` | HeadingChunker (300) | 15 | 181.7 | ✅ |
| `shopee_buyer_non_returnable` | FixedSizeChunker (300, overlap=0) | 6 | 279.2 | ❌ |
| `shopee_buyer_non_returnable` | SentenceChunker (3 câu) | 4 | 417.0 | ✅ |
| `shopee_buyer_non_returnable` | RecursiveChunker (300) | 8 | 207.5 | ✅ |
| `shopee_buyer_non_returnable` | HeadingChunker (300) | 10 | 165.6 | ✅ |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Nguyễn Minh Thắng (2A202602706)**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=50)`
- **Mô tả & lý do chọn cho chủ đề này:** Baseline kiểm soát rõ kích thước và có overlap để giảm mất mát ở ranh giới. Đây là đối chứng cần thiết khi so sánh với hai chiến lược theo cấu trúc.
```python
FixedSizeChunker(chunk_size=500, overlap=50)
```

**Thành viên 2 — Nguyễn Minh Tuấn (2A202602420)**
- **Loại chiến lược:** `SentenceChunker(max_sentences_per_chunk=3)`
- **Mô tả & lý do chọn:** Chính sách thường diễn đạt một điều kiện hoặc mốc thời gian bằng câu hoàn chỉnh. Gom ba câu giữ được ngữ nghĩa mà không tạo chunk quá dài.

**Thành viên 3 — Nguyễn Thị Vàng (2A202602897)**
- **Loại chiến lược:** `HeadingChunker(chunk_size=500, min_heading_level=3)` (custom)
- **Mô tả & lý do chọn:** Các file chính sách Markdown đã chia theo `##`/`###`, mỗi mục là đơn vị nghiệp vụ tương đối trọn vẹn. Khi section vượt ngưỡng, tôi dùng RecursiveChunker cho phần thân và gắn lại heading vào mọi mảnh con để các mảnh sau không mất chủ đề.
- **Code snippet (nếu custom):**
```python
HeadingChunker(chunk_size=500, min_heading_level=3)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Nguyễn Minh Thắng | FixedSize(500, overlap=50) | top-1 1/5; top-3 2/5 (doc-level) | Kích thước ổn định, có overlap | Có thể cắt câu/section |
| Nguyễn Minh Tuấn | SentenceChunker(3) | R2 báo cáo: top-1 1/5; top-3 4/5 | Giữ câu đầy đủ | Không giữ heading riêng |
| Nguyễn Thị Vàng | HeadingChunker(500) | R3 báo cáo: top-1 2/5; top-3 2/5 | Chunk tự mô tả, dễ debug | Phụ thuộc chất lượng đề mục |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Với MockEmbedder, các số liệu chỉ dùng để quan sát tác động của cách chia chunk, không dùng để kết luận semantic retrieval. R3 (Vàng) có top-1 cao hơn trên phép đo báo cáo nhờ heading tự mô tả; R2 (Tuấn) có top-3 cao hơn nhờ giữ câu đầy đủ. Cần đo lại bằng multilingual embedder thật trước khi chọn chiến lược triển khai.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| Q1 | Người bán phải phản hồi yêu cầu trả hàng trong bao nhiêu ngày? | Người bán phản hồi Trả hàng/Hoàn tiền trong **3 ngày làm việc** kể từ khi nhận thông báo. | `shopee_seller_dispute_response` / `### Thời gian phản hồi tiêu chuẩn` |
| Q2 | Đơn hàng thực phẩm tươi sống bị khiếu nại cần phản hồi trong bao lâu? *(filter: seller)* | Thực phẩm tươi sống & đông lạnh: phản hồi trong **24 giờ**. | `shopee_seller_dispute_response` / `### Các trường hợp đặc biệt` |
| Q3 | Điều kiện trả hàng điện tử DOA của người mua là gì? *(filter: buyer)* | **30 ngày** từ khi nhận hàng; chưa sử dụng, còn nguyên seal và phụ kiện. | `shopee_buyer_return_timeline` / `### 2.3. ... (DOA)` |
| Q4 | Hậu quả khi người bán không phản hồi khiếu nại đúng hạn là gì? | Shopee tự động chấp nhận yêu cầu; phản hồi trễ có thể ảnh hưởng **điểm đánh giá cửa hàng**. | `shopee_seller_dispute_response` / `## 4. Hậu quả...` |
| Q5 | Video bằng chứng đóng gói gửi Shopee cần đáp ứng gì? | Video xuyên suốt, không cắt ghép; không quá **100MB/video**, tối đa **1 phút**, MP4 hoặc AVI. | `shopee_seller_evidence_guide` / `## 4. Yêu cầu về bằng chứng` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| Q1 | Thời hạn phản hồi seller | Heading (R3: top-1) | Có ở doc-level | FixedSize (R1) chỉ có gold ở top-2; cần chấm marker nội dung thay vì doc_id. |
| Q2 | Thực phẩm tươi 24 giờ | Heading (R3: top-1) | Có ở doc-level | Filter `seller` đưa gold document lên top-1 cho FixedSize, nhưng chưa đủ context 24 giờ. |
| Q3 | Điều kiện DOA buyer | Sentence (R2: top-1) | Có | FixedSize (R1) miss; câu này cần giữ câu/điều kiện đầy đủ. |
| Q4 | Hậu quả không phản hồi | Chưa có chiến lược đạt | Không | Mock trả về các chunk seller/buyer cùng từ khoá nhưng không có section hậu quả. |
| Q5 | Yêu cầu video bằng chứng | Sentence (R2: top-3) | Có ở doc-level | Doc-level hit chưa đủ: phải có đúng section 100MB/1 phút/định dạng. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có ích ở Q2 theo nghĩa lọc trước loại bỏ toàn bộ tài liệu buyer: FixedSize của Thắng đổi từ không có gold document sang có `shopee_seller_dispute_response` ở top-1. Tuy nhiên chưa thể gọi là trả lời đúng vì section 24 giờ vẫn không vào context. Q3 hầu như không đổi với MockEmbedder; cần thay query mơ hồ hơn hoặc dùng semantic embedder để chứng minh precision/recall một cách đáng tin cậy.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. Chấm theo `doc_id` thổi phồng kết quả: Q1/Q2 có thể truy xuất đúng tài liệu nhưng sai section nên thiếu đáp án.  
> 2. Filter audience là pre-filter, có thể tăng precision nhưng cũng không tự khắc phục ranking trong phần candidate còn lại.  
> 3. Count và avg length vẫn là chỉ số đáng tin khi dùng MockEmbedder: Heading tạo 99 chunks (197.3 ký tự/chunk) trên toàn corpus, nhỏ và có cấu trúc hơn Sentence (41 chunks, 474.8 ký tự/chunk).

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus, FixedSize ưu tiên kích thước, Sentence ưu tiên nguyên vẹn câu, còn Heading ưu tiên đơn vị nghiệp vụ. Heading cần nhiều chunk hơn do section dài được chia nhỏ nhưng giữ lại heading; đổi lại, mỗi mảnh có thể tự giải thích chủ đề. Kết quả retrieval hiện bị chi phối bởi MD5 mock nên nhóm không dùng chúng để khẳng định chiến lược tốt hơn về semantic search.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Đồng bộ PyTorch và dùng multilingual sentence-transformer trước khi đo lại; sau đó giữ HeadingChunker theo hướng heading + recursive body. Nhóm cũng sẽ viết lại một query thật sự mơ hồ giữa buyer/seller để A/B filter thể hiện rõ đánh đổi precision–recall.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | 12 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 8 / 10 (tạm đánh giá) |
| Thuyết trình (Demo) | Chờ demo / 5 |
| **Tổng phần nhóm** | **30+ / 40** |
