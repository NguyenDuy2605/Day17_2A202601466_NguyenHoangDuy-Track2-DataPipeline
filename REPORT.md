# Báo cáo LAB 17 — Data Pipeline Engineering

**Họ tên:** Nguyễn Hoàng Duy **Lớp:** E403 **Ngày:** 2026-08-17

> **Cách tái lập trên máy sạch** — `data/` nằm trong `.gitignore` nên phải sinh
> lại, và bài mở rộng A đã đổi `queries/dashboard.sql` sang dataset đã compact:
>
> ```bash
> make setup     # venv + thư viện + 14 ngày dữ liệu
> make extra     # = seed-extra + compact  (sinh data/gold_events + gold_events_v2)
> make verify    # 3 lượt + bảng chấm
> make crash-test
> ```
>
> `expected/dashboard_baseline.json` được commit sẵn trong repo gốc, nên
> `make verify` sẽ đo `queries/dashboard.sql` ngay cả khi chưa có `data/` —
> vì thế `make extra` cần chạy **trước** `make verify` (target `extra` là chỗ
> duy nhất tôi thêm vào Makefile, nó chỉ gọi lại hai target có sẵn).

---

## 0 · Kết quả `make verify`

<details>
<summary>Output ba lượt chạy liên tiếp (make verify)</summary>

```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LAB 17 · make verify
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  run 1/3 … 32.9s
  run 2/3 … 27.4s
  run 3/3 … 24.9s

  BẢNG                  ỔN ĐỊNH          SỐ HÀNG     KỲ VỌNG   GHI CHÚ
  ──────────────────────────────────────────────────────────────────────────
  gold_training_set     ✓ ok              12,480      12,480   ✓
  gold_feature_daily    ✓ ok               9,100       9,100   ✓
  gold_doc_chunks       ✓ ok              31,200      31,200   ✓
  quarantine_tickets    ✓ ok                 312         312   ✓

  CHECKSUM từng lượt
  ──────────────────────────────────────────────────────────────────────────
  gold_training_set     8dd7c98653    8dd7c98653    8dd7c98653   ✓
  gold_feature_daily    3db448685c    3db448685c    3db448685c   ✓
  gold_doc_chunks       92d8e50131    92d8e50131    92d8e50131   ✓
  quarantine_tickets    ebb89036fb    ebb89036fb    ebb89036fb   ✓

  KIỂM TRA KHÁC
  ──────────────────────────────────────────────────────────────────────────
  dbt test                                    ✓ 19/19 pass
  silver_tickets.priority ∈ 1..4, không NULL  ✓ sạch
  quarantine_tickets đúng số bản ghi lỗi      ✓ 312 / 312
  gold_training_set: 1 hàng / 1 ticket        ✓ không lặp
  dashboard rows scanned                      ✓ 5,000,000 → 9,324 (536.3×, cần ≥ 10×)
    số file parquet                           ✓ 5,000 → 14
    kết quả truy vấn không đổi                ✓
  DAG: catchup / max_active_runs              ✓ False / 1

  TỔNG KẾT
  ──────────────────────────────────────────────────────────────────────────
  ✓  1 · gold_training_set idempotent & đúng số hàng
  ✓  2 · gold_feature_daily đủ hàng (dữ liệu về muộn)
  ✓  3 · contract + quarantine + dbt test
  ✓  4 · gold_doc_chunks vẫn ổn định (đối chứng)
  ──────────────────────────────────────────────────────────────────────────
  4/4 tiêu chí đạt
```

</details>

<details>
<summary>Lượt thứ 4 và thứ 5 (chạy tiếp trên chính kho đó, không reset)</summary>

```
  run 1/2 … 29.5s
  run 2/2 … 25.6s

  BẢNG                  ỔN ĐỊNH          SỐ HÀNG     KỲ VỌNG   GHI CHÚ
  ──────────────────────────────────────────────────────────────────────────
  gold_training_set     ✓ ok              12,480      12,480   ✓
  gold_feature_daily    ✓ ok               9,100       9,100   ✓
  gold_doc_chunks       ✓ ok              31,200      31,200   ✓
  quarantine_tickets    ✓ ok                 312         312   ✓

  CHECKSUM từng lượt
  ──────────────────────────────────────────────────────────────────────────
  gold_training_set     8dd7c98653    8dd7c98653   ✓
  gold_feature_daily    3db448685c    3db448685c   ✓
  gold_doc_chunks       92d8e50131    92d8e50131   ✓
  quarantine_tickets    ebb89036fb    ebb89036fb   ✓
```

Checksum của lượt 4 và 5 trùng khớp với cả ba lượt đầu — bảng hội tụ, không
trôi theo số lần chạy.

</details>

Tổng kết: **4 / 4 tiêu chí đạt** · hai bài mở rộng: **A ĐẠT**, **B ĐẠT**.

---

## 1 · Kích thước bảng training tăng sau mỗi lần chạy

|                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Triệu chứng**    | `gold_training_set` = 38.750 hàng sau 3 lượt (thừa 26.270), 12.480 ticket bị lặp, checksum ba lượt khác nhau. Không có lỗi nào được báo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Nguyên nhân**    | Model khai báo `materialized='incremental'` nhưng **không khai `unique_key`**, nên dbt sinh ra một câu `INSERT INTO gold_training_set SELECT …` thuần. Phép ghi này không có khái niệm "hàng này đã tồn tại": bảng có grain **entity** (1 ticket) nhưng lại đang được ghi bằng ngữ nghĩa **append của một event log**. Vì bản thân phép ghi không idempotent, **mọi cơ chế chạy lại ở tầng trên đều bị biến thành cơ chế nhân bản** — Clear Task của người trực, `retries=2` trong `default_args`, và `catchup=True` khi DAG được bật lại. Tệ hơn: nguồn CDC có `op='u'`, nên một ticket tạo ngày D1 rồi sửa ngày D2 lọt qua mệnh đề `WHERE _ingested_at ∈ [run_date, run_date+1)` ở **hai run_date khác nhau** — nghĩa là ngay cả một lượt chạy sạch, không sự cố, cũng đã tự nhân đôi 1.310 ticket. Đây là lý do "xoá partition của ngày rồi ghi lại" cũng không cứu được: hai bản của cùng một ticket nằm ở hai partition ngày khác nhau. |
| **Cách khắc phục** | `dbt/models/gold/gold_training_set.sql`: thêm `unique_key='ticket_id'` và `incremental_strategy='merge'` → bản ghi mới **thay thế** bản ghi cùng khoá bất kể nó thuộc partition ngày nào. `dags/ai_training_pipeline.py`: `catchup=False`, `max_active_runs=1` (chỉ giảm tần suất kích hoạt, **không** phải root cause). Thêm test `unique`+`not_null` trên `gold_training_set.ticket_id` để lần sau vi phạm grain thì `dbt test` đỏ ngay, không đợi ai đếm tay.                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Bằng chứng**     | trước: 38.750 hàng, 12.480 ticket lặp · sau: **12.480** hàng, 0 lặp · checksum 5 lượt: `8dd7c98653` × 5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

**Kiểm chứng cơ chế bằng số học** — con số 38.750 phân tích được trọn vẹn, đúng
đến từng hàng, nên đây không phải suy đoán:

```
lượt 1 :  12.480  (mỗi ticket một lần)
        +  1.310  (ticket có bản ghi op='u' -> lọt qua WHERE ở HAI run_date)
        = 13.790
lượt 2 : +12.480  (Silver đã đủ 14 ngày, mỗi ticket khớp đúng một run_date)
lượt 3 : +12.480
        = 38.750  ✔ đúng bằng con số quan sát được ở trạng thái ban đầu
```

Hai điều rút ra: (a) `1.310` đúng bằng số bản ghi `op='u'` trong
`bronze_tickets_cdc` (998 cập nhật hợp lệ + 312 cập nhật sai kiểu) — tức là bảng
đã sai **ngay từ lượt chạy đầu tiên**, trước cả khi có ai bấm Clear Task;
(b) từ lượt 2 trở đi mỗi lượt cộng đúng 12.480 hàng — tăng trưởng tuyến tính,
không hội tụ, nên lỗi này không thể tự khỏi bằng cách "chạy lại cho sạch".

---

## 2 · Bảng đặc trưng theo ngày thiếu hàng ở các ngày quá khứ

|                        |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Triệu chứng**        | `gold_feature_daily` = 8.645 / 9.100 hàng (thiếu **455**), nhưng cột `ỔN ĐỊNH` lại ✓ — sai một cách rất ổn định. Chỉ thiếu ở các ngày đã chạy xong từ lâu.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **P99 độ trễ đo được** | **2,73 ngày** _(P50 = 0,13 · P95 = 1,81 · max = 2,94 · 5,05% bản ghi tới muộn hơn 1 ngày; đo trên 129.462 hàng `bronze_events`)_                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Lookback đã chọn**   | **3 ngày** — làm tròn LÊN từ P99 (2,73) và vẫn phủ cả max (2,94). Kiểm chứng theo ngày lịch: `max(date_diff('day', event_date, ingested_date)) = 3`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Nguyên nhân**        | Điều kiện `where event_date > (select max(event_date) from {{ this }})` trộn lẫn **hai trục thời gian khác nhau**: nó lọc theo `event_date` — thời điểm sự kiện **xảy ra** — trong khi dữ liệu tới kho theo `_ingested_at` — thời điểm sự kiện **tới**. `max(event_date)` là một watermark **chỉ tiến, không bao giờ lùi**: ngay khi một event của ngày mới đến đúng giờ được nạp, mốc nhảy lên ngày đó và **mọi** event của các ngày trước bị loại vĩnh viễn — kể cả những event vừa mới tới kho lần đầu. Nói cách khác, cửa sổ xử lý của một ngày bị đóng bởi _dữ liệu đến đúng hạn của ngày kế tiếp_, chứ không phải bởi _dữ liệu của ngày đó đã đầy đủ_. Với phân bố trễ có đuôi tới 2,94 ngày, 455 cặp (ngày, khách) mà **toàn bộ** event đều về muộn không bao giờ có cơ hội lọt vào bảng — thiếu đúng 455 hàng. Bảng vẫn "ổn định" vì lỗi mang tính hệ thống và tất định, chứ không phải ngẫu nhiên. |
| **Cách khắc phục**     | `dbt/models/gold/gold_feature_daily.sql`: đổi thành `where event_date >= (select max(event_date) from {{ this }}) - interval 3 day`, đồng thời thêm `unique_key=['event_date','customer_id']` + `incremental_strategy='delete+insert'`. Ý thứ hai là bắt buộc: nới cửa sổ mà không có khoá thì cùng một cặp (ngày, khách) được tính lại ở nhiều lượt và **cộng dồn** — tái tạo đúng lỗi của nhiệm vụ 1 trên một bảng khác.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Bằng chứng**         | trước: 8.645 hàng · sau: **9.100** hàng · checksum 5 lượt: `3db448685c` × 5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

**Vì sao chọn P99 làm căn cứ thay vì `max`? Chi phí của mỗi lựa chọn là gì?**

> `max` là một quan sát của **một** bản ghi cá biệt trong quá khứ; nó không có
> giới hạn trên và sẽ trôi theo mỗi lần nguồn có sự cố. Lấy `max` làm căn cứ
> nghĩa là để bản ghi tệ nhất từng thấy quyết định chi phí của **mọi** lượt
> chạy về sau. Mỗi ngày lookback thêm phải trả giá thường xuyên — quét lại và
> ghi lại 650 khách × 1 ngày, ở mọi lượt chạy, mãi mãi — chứ không phải trả
> một lần.
>
> P99 là một ngưỡng có thể chịu trách nhiệm được: nó nói "99% dữ liệu về muộn
> sẽ được cửa sổ này bắt kịp", và phần đuôi còn lại được xử lý bằng **backfill
> có chủ đích** khi cần, thay vì bằng cách kéo dài cửa sổ vĩnh viễn cho mọi
> lượt chạy. Ở bộ dữ liệu này P99 (2,73) và max (2,94) làm tròn lên cùng ra
> **3 ngày**, nên lựa chọn an toàn mà không tốn thêm gì — nhưng con số cần được
> đo lại định kỳ: khi phân bố trễ đổi, lookback phải đổi theo, và đó là lý do
> nó được viết thành một biến `lookback_days` đặt ngay cạnh số đo trong file.

**Biên an toàn của lookback (đo được, không phải ước lượng).** Mốc so sánh là
`max(event_date)` của **bảng đích**, mà bảng đích chỉ chứa dữ liệu đã nạp đến
hết ngày hôm trước — nên bản thân mốc đã trễ một ngày so với ngày vận hành. Đo
trực tiếp trên dữ liệu: với mọi ngày nạp `D`, chênh lệch giữa mốc lúc đó và
`event_date` nhỏ nhất của lô vừa tới lớn nhất là **2 ngày**. Tức lookback tối
thiểu đủ dùng là 2, và lookback 3 đang có **1 ngày dự phòng** — đủ chỗ cho một
đợt trễ xấu hơn hiện tại mà không phải sửa code.

**Kiểm chứng độ đúng của giá trị, không chỉ số hàng.** Số hàng đúng và checksum
ổn định vẫn có thể che một bảng sai **giá trị**: nếu dữ liệu muộn rơi ra ngoài
lookback, hàng `(ngày, khách)` vẫn tồn tại nhưng `n_events` bị thiếu, và cả ba
lượt chạy đều thiếu giống hệt nhau nên `make verify` không thể phát hiện. Vì
vậy tôi đối chiếu bảng incremental với bản **tính lại toàn bộ** từ Silver
(`EXCEPT` hai chiều, so từng ô của cả 11 cột):

| Đối chiếu | Lệch |
|---|---|
| `gold_feature_daily` ⟷ tính lại toàn bộ từ `silver_events` | **0** hàng (cả hai chiều) |
| `gold_training_set` ⟷ tính lại toàn bộ từ `silver_tickets` | **0** hàng (cả hai chiều — không sót, không còn hàng cũ) |
| Cặp `(event_date, customer_id)` có trong Silver mà thiếu ở Gold | **0** |

Nói cách khác: hai bảng incremental cho kết quả **không phân biệt được** với
một bảng dựng lại từ đầu — đó mới là định nghĩa đầy đủ của "incremental đúng",
còn tính ổn định chỉ là điều kiện cần.

---

## 3 · Kiểu dữ liệu cột `priority` thay đổi giữa chu kỳ

|                                              |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Triệu chứng**                              | Pipeline không hề dừng, `dbt test` 9/9 pass, nhưng 6.606 hàng `silver_tickets.priority` sai (NULL, hoặc 0 / 5 / −1), và model phân loại dự đoán kém hẳn kể từ 08-10.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Nguyên nhân**                              | Chuẩn hoá đang dùng `try_cast(priority_raw as integer)` — một phép ép kiểu **im lặng**: cái gì không parse được thì thành `NULL`, không phát ra tín hiệu lỗi nào. Khi backend đổi cách biểu diễn từ số sang nhãn chữ ngày 08-10, toàn bộ `urgent`/`high`/`medium`/`low` rơi vào `NULL` — dữ liệu **hoàn toàn hợp lệ** bị xoá nhãn, mà không có gì chặn lại vì `contract: enforced: false` (dbt không kiểm kiểu) và không có test nào ràng buộc miền giá trị. Đồng thời `try_cast` **chấp nhận** `'0'`, `'5'`, `'-1'` vì chúng đúng là số nguyên — dù contract quy định 1..4 — nên dữ liệu hỏng thật lại đi thẳng vào Silver. Một phép ép kiểu im lặng sai theo **hai hướng ngược nhau cùng lúc**: loại nhầm dữ liệu tốt và nhận nhầm dữ liệu xấu. Thứ bị mất không phải là dữ liệu, mà là **tín hiệu**: sau `try_cast`, không còn gì phân biệt "không parse được" với "hợp lệ nhưng rỗng", nên hạ nguồn không có cách nào biết mình đang học trên nhãn rỗng.                                                            |
| **Ba nhóm giá trị `priority` và cách xử lý** | **(1) Số hợp lệ** `1 2 3 4` (6.846 bản ghi) — đúng contract cũ → **giữ nguyên**. **(2) Nhãn chuỗi** `urgent high medium low` (7.142) — _schema evolution_: ý nghĩa không đổi, chỉ đổi cách biểu diễn → **map về 1..4** theo tài liệu API (urgent=1, high=2, medium=3, low=4). **(3) Không hợp lệ** `P1 P2 unknown 0 5 -1 '' NULL` (312) — dữ liệu lỗi thật → **quarantine**. Tiêu chí phân biệt nhóm 2 và 3: _giá trị này có mang đúng thông tin của contract cũ, chỉ khác cách viết hay không?_ Đối xử với nhóm 2 như nhóm 3 sẽ vứt 7.142 bản ghi tốt và làm quarantine phình lên hàng nghìn hàng.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Cách khắc phục**                           | `dbt/macros/normalize_priority.sql`: thay `try_cast` bằng khối `CASE` xử lý đủ ba nhóm, trong đó nhóm 1 phải kèm `between 1 and 4` (số nằm ngoài miền cũng là lỗi), trả `NULL` cho nhóm 3 — dùng `NULL` làm **tín hiệu** thay vì làm chỗ đổ rác. `silver_tickets.sql`: **lọc trước, xếp hạng sau** — loại _bản ghi_ CDC hỏng ở CTE `valid_cdc` rồi mới `row_number()`, nên ticket có bản ghi mới nhất bị hỏng vẫn giữ trạng thái hợp lệ của lần cập nhật trước (nếu lọc sau khi xếp hạng, số ticket tụt còn 12.168). `quarantine_tickets.sql`: `where {{ normalize_priority('priority_raw') }} is null` — đúng điều kiện **phủ định** của Silver, cùng một macro nên hai bên không thể lệch nhau; kèm `priority_reject_reason` phân loại 4 kiểu lỗi cho người trực. `schema.yml`: `contract: enforced: true` + test `not_null` và `accepted_values [1,2,3,4]`. Thêm hai singular test trong `dbt/tests/`: grain (ticket_id, cdc_seq) của quarantine, và bất biến "Silver ∪ Quarantine rời nhau và phủ hết bản ghi CDC". |
| **Bằng chứng**                               | `quarantine_tickets` = **312** hàng / 312 ticket, toàn bộ là `op='u'`, grain 1 hàng / 1 bản ghi CDC · `silver_tickets` = **12.480** ticket, `priority` phân bố 3.134 / 3.029 / 3.115 / 3.202 cho 1/2/3/4, không NULL · `dbt test` **19/19 pass** (bản gốc 9 test → thêm 10)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

**Câu hỏi thiết kế: nên chặn ở tầng Bronze hay Silver? Vì sao không để pipeline dừng?**

> **Chặn ở Silver.** Bronze là _sự thật của nguồn_ — payload gốc, không phán
> xét, không ép kiểu; Silver là _sự thật đã được kiểm định_. Nếu Bronze từ chối
> bản ghi lỗi thì bản ghi gốc không còn tồn tại ở đâu cả, và ta mất hai thứ:
> (a) khả năng điều tra — không trả lời được "nguồn thực sự đã gửi cái gì lúc
> 08-10", chỉ còn suy đoán từ chỗ trống; (b) khả năng **replay** — chính sự cố
> này là ví dụ: lúc đầu `urgent`/`high` trông như rác, sau khi đọc tài liệu API
> mới biết đó là dữ liệu hợp lệ đổi format. Sửa được logic là vì Bronze còn giữ
> nguyên bản; nếu Bronze đã vứt, 7.142 bản ghi đó mất vĩnh viễn và không lệnh
> nào lấy lại được.
>
> **Không dừng DAG**, vì quy mô không cho phép: 312 bản ghi hỏng trên 14.300
> bản ghi CDC (2,2%). Dừng pipeline nghĩa là để 312 bản ghi hỏng chặn 12.480
> ticket, 130.683 event và 31.200 chunk hoàn toàn bình thường đến tay người
> dùng — đổi một lỗi cục bộ, có thể xử lý nguội, lấy một sự cố toàn hệ thống,
> ngay lập tức. Fail-fast là đúng khi lỗi mang tính **hệ thống** (schema đổi
> toàn bộ, nguồn chết, 100% bản ghi sai); với lỗi **theo từng bản ghi**, cách
> đúng là định tuyến sang dead-letter queue và cảnh báo theo **ngưỡng** — test
> nên canh "số bản ghi quarantine tăng đột biến" chứ không phải "có bản ghi
> quarantine". Bảng `quarantine_tickets` vì thế là hàng đợi công việc của người
> trực, và cột `reject_reason` là để họ biết ngay phải làm gì.

---

## 4 · Bài mở rộng

### Bài A — Query dashboard chậm

|                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Triệu chứng**    | Dashboard 38 giây (ba tháng trước 2 giây), không ai sửa dòng code nào. `rows scanned` = 5.000.000 cho một tập chỉ có 130.683 hàng thật.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Nguyên nhân**    | `data/gold_events/` là 5.000 file Parquet, trung bình ~26 hàng/file, không partition, thứ tự hàng ngẫu nhiên. Engine chỉ bỏ qua được một file khi nó biết file đó vô ích **trước khi mở** — và thông tin đó chỉ có thể đến từ **đường dẫn**. Ở đây đường dẫn (`part-00123.parquet`) không mang thông tin của bất kỳ cột lọc nào, nên engine buộc phải mở cả 5.000 file rồi mới biết file nào có ích; mỗi file lại tốn một lô đọc tối thiểu (~1.000 hàng) dù chỉ chứa 26 hàng → 5.000.000 đơn vị công quét. Đó là small-file problem hiện thành con số. Cộng thêm một lỗi thứ hai ở phía query: `strftime(event_time,'%Y-%m-%d') = '2026-08-09'` bọc cột trong một function call, nên predicate **không sargable** — engine không so được kết quả function với tên thư mục partition, cũng không so được với thống kê min/max của row group. Query không đổi mà chậm dần vì chi phí nằm ở **layout của dữ liệu**, và layout thì xấu đi theo thời gian mỗi khi có thêm file. |
| **Cách khắc phục** | `tools/compact.py`: `COPY … TO 'data/gold_events_v2' (partition_by (event_date), row_group_size 2048)` với `order by customer_name, event_time`. Ba quyết định: **partition theo `event_date`** (14 giá trị → 14 thư mục ~9.300 hàng; partition theo `customer_name` với 650 giá trị sẽ tái tạo đúng small-file problem đang phải sửa); **sắp xếp theo `customer_name`** để hàng của một khách nằm liền nhau, min/max của row group mới loại được row group thay vì chỉ mô tả nó; **`row_group_size` 2048** vì mặc định 122.880 > số hàng của cả một ngày, tức cả ngày gói trong MỘT row group và min/max của nó trải từ 'ACME' tới 'Cust_0650' — vô dụng. `queries/dashboard.sql`: trỏ vào dataset mới, bật `hive_partitioning=true`, viết lại predicate thành `event_date = '2026-08-09'` để cột đứng một mình.                                                                                                                                                          |
| **Bằng chứng**     | `rows scanned` **5.000.000 → 9.324** (giảm **536,3×**, cần ≥ 10×) · `files` **5.000 → 14** · `rows on disk` 130.683 (không mất hàng: assert trong `compact.py`) · `result hash` **4379e4c5d9f3 → 4379e4c5d9f3** (không đổi) · thời gian 5,6 ms                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

### Bài B — Consumer gặp sự cố giữa batch

|                    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Triệu chứng**    | Consumer bị `kill -9` ở lô thứ 7. Tái hiện lại đúng thứ tự gốc cho thấy: offset đã commit = **3.500** trong khi kho mới chỉ có **3.000** hàng (6 lô đầu). Khởi động lại đọc tiếp từ message 3.501 → **mất trọn 500 message của lô 7**, im lặng, không lỗi, không cách nào phát hiện nếu chỉ nhìn log.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Nguyên nhân**    | `consume()` gọi `consumer.commit()` **trước** `write_batch()`. Offset và dữ liệu nằm trên hai hệ thống lưu trữ khác nhau, không có transaction chung, nên giữa hai thao tác luôn tồn tại một cửa sổ mà offset đã tuyên bố "lô này xử lý xong" trong khi kho chưa hề có nó. Chết trong cửa sổ đó là **mất dữ liệu vĩnh viễn** — đó chính là định nghĩa **at-most-once**. Cửa sổ này không thể xoá được bằng cách viết code cẩn thận hơn: _exactly-once không tồn tại ở tầng giao vận_. Thứ duy nhất chọn được là **hướng** của sai số — mất hay trùng — và trùng thì khử được, mất thì không.                                                                                                     |
| **Cách khắc phục** | `ingest/consumer.py`: (a) đảo thứ tự thành **ghi trước, commit sau** → chuyển sang **at-least-once**, crash làm lô 7 được đọc lại chứ không bị bỏ qua; (b) khử phần trùng bằng **phép ghi idempotent**: thêm `primary key` cho `event_id` trong DDL và đổi `INSERT` thành `INSERT … ON CONFLICT (event_id) DO UPDATE SET …`. Chọn `DO UPDATE` chứ không `DO NOTHING`: nếu một message được phát lại với nội dung **đã đổi**, `DO NOTHING` giữ lại phiên bản cũ — dữ liệu lỗi thời một cách im lặng; `DO UPDATE` luôn hội tụ về phiên bản mới nhất, nên kết quả cuối chỉ phụ thuộc **tập** message đã xử lý chứ không phụ thuộc mỗi message được xử lý mấy lần. Đó đúng là định nghĩa idempotent. |
| **Bằng chứng**     | Trước (thứ tự gốc): offset 3.500 / kho 3.000 → mất 500. Sau: A (chạy thẳng) = 20.000 hàng / 20.000 `event_id` · B = chết ở lô 7, offset commit **3.000** (đúng bằng phần đã ghi xong — offset không còn chạy trước dữ liệu) · C (restart, phát lại 17.000 message trong đó 500 message của lô 7 là bản trùng) = **20.000 hàng / 20.000 `event_id`** → không mất, không trùng, **C == A**. `make crash-test`: **ĐẠT ✓**; `make verify` vẫn 4/4.                                                                                                                                                                                                                                                                                                                                                                                                                                   |

---

## 5 · Tổng kết

| Nhiệm vụ | Khi tiếp nhận một hệ thống chưa quen, tôi sẽ kiểm tra điều này trước tiên                                                                                                                                                                                                                                                                                                                    |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1        | Chạy pipeline **hai lần liên tiếp trên cùng một input** rồi so checksum. Một hệ thống không idempotent thường không báo lỗi — nó chỉ âm thầm sai thêm mỗi lần retry. Cụ thể hơn: với mọi model `incremental`, đọc SQL **thật** dbt sinh ra (`dbt/target/run/…`) và trả lời "phép ghi này là INSERT hay UPSERT?" trước khi tin vào tên materialization.                                       |
| 2        | Với mọi bộ lọc incremental, hỏi **mốc so sánh lấy từ trục thời gian nào** — thời điểm sự kiện xảy ra hay thời điểm nó tới kho — và đo **phân bố độ trễ** giữa hai trục đó (P50/P95/P99/max). Watermark chỉ tiến trên trục "xảy ra" luôn đồng nghĩa với việc lặng lẽ vứt dữ liệu về muộn. Đi kèm: một bảng "ổn định" chưa chắc đúng — ổn định và đúng là hai phép đo tách biệt.               |
| 3        | Tìm mọi chỗ ép kiểu **im lặng** (`try_cast`, `coalesce`, `safe_cast`) ở biên giới với nguồn dữ liệu, và kiểm tra contract/test có thật sự đang bật không. Ở đó, `NULL` có thể mang hai nghĩa hoàn toàn khác nhau — "không có giá trị" và "không parse được" — và khi hai nghĩa đó bị trộn, lỗi không bao giờ nổi lên ở tầng pipeline mà chỉ hiện ra ở chất lượng model, muộn hơn nhiều tuần. |

### Bảng tự chấm nhanh

|                                       | Của tôi                                                                  | Kỳ vọng        | ✓/✗ |
| ------------------------------------- | ------------------------------------------------------------------------ | -------------- | --- |
| `gold_training_set` — số hàng         | 12.480                                                                   | 12.480         | ✓   |
| `gold_training_set` — ổn định 3 lượt  | `8dd7c98653` × 5 lượt                                                    | ✓              | ✓   |
| `gold_feature_daily` — số hàng        | 9.100                                                                    | 9.100          | ✓   |
| `gold_feature_daily` — ổn định 3 lượt | `3db448685c` × 5 lượt                                                    | ✓              | ✓   |
| `gold_doc_chunks` — số hàng           | 31.200                                                                   | 31.200         | ✓   |
| `quarantine_tickets` — số hàng        | 312                                                                      | 312            | ✓   |
| `silver_tickets` — số ticket          | 12.480                                                                   | 12.480         | ✓   |
| `dbt test`                            | 19/19 pass (bản gốc 9)                                                   | pass, > 9 test | ✓   |
| P99 độ trễ đo được                    | **2,73 ngày** (max 2,94 · late 5,05%)                                    | (ghi số)       | ✓   |
| **Tổng verify**                       | 4/4                                                                      | 4/4 tiêu chí   | ✓   |
| _(thưởng)_ Bài A                      | 5.000.000 → 9.324 rows scanned (536,3×), 5.000 → 14 file, hash không đổi | ≥ 10×          | ✓   |
| _(thưởng)_ Bài B                      | `make crash-test`: ĐẠT — không mất, không trùng                          | ĐẠT            | ✓   |

### Các file đã sửa

| File                                                                                 | Nhiệm vụ                                                 |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| `dbt/models/gold/gold_training_set.sql`                                              | 1 — `unique_key` + `incremental_strategy='merge'`        |
| `dags/ai_training_pipeline.py`                                                       | 1 — `catchup=False`, `max_active_runs=1`                 |
| `dbt/models/gold/gold_feature_daily.sql`                                             | 2 — lookback 3 ngày + `unique_key` kép + `delete+insert` |
| `dbt/macros/normalize_priority.sql`                                                  | 3 — `CASE` ba nhóm + `priority_reject_reason`            |
| `dbt/models/silver/silver_tickets.sql`                                               | 3 — lọc trước, xếp hạng sau                              |
| `dbt/models/silver/quarantine_tickets.sql`                                           | 3 — điều kiện phủ định của Silver                        |
| `dbt/models/silver/schema.yml`                                                       | 3 — `contract: enforced: true` + test miền giá trị       |
| `dbt/models/gold/schema.yml`                                                         | 1, 2 — test grain cho các bảng Gold                      |
| `dbt/tests/quarantine_tickets_grain.sql`, `dbt/tests/silver_quarantine_disjoint.sql` | 3 — hai singular test mới                                |
| `tools/compact.py`, `queries/dashboard.sql`                                          | mở rộng A                                                |
| `ingest/consumer.py`                                                                 | mở rộng B                                                |
