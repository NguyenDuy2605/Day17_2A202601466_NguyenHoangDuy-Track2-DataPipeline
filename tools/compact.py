#!/usr/bin/env python3
"""Tái cấu trúc dataset Parquet của dashboard — NHIỆM VỤ 4.  CHƯA CÓ LOGIC.

Hiện trạng: `data/gold_events/` gồm 5.000 file, mỗi file vài chục KB, không
partition, thứ tự hàng ngẫu nhiên.

Yêu cầu: đọc toàn bộ dataset cũ, ghi ra dataset mới có layout hợp lý hơn, sau đó cập
nhật `queries/dashboard.sql` để trỏ vào dataset mới.

    python tools/compact.py       # ghi dataset mới
    python tools/explain.py       # đo lại và so với baseline

KHUNG THỰC HIỆN

    COPY (
        SELECT *
        FROM   read_parquet('data/gold_events/*.parquet')
        ORDER  BY <cột A>, <cột B>
    ) TO 'data/gold_events_v2' (
        FORMAT          parquet,
        PARTITION_BY    (<cột partition>),
        OVERWRITE_OR_IGNORE,
        ROW_GROUP_SIZE  <?>
    )

Ba quyết định, mỗi quyết định cần một lý do viết được ra giấy:

  <cột partition>   Engine chỉ bỏ qua được file mà nó biết là vô ích TRƯỚC khi
                    mở file. Thông tin đó đến từ đường dẫn. Vậy cột nào của
                    truy vấn dashboard nên xuất hiện trong tên thư mục? Cột đó
                    có bao nhiêu giá trị phân biệt — tức bao nhiêu thư mục?
                    Partition theo cột có 650 giá trị thì hệ quả là gì?

  <cột A>, <cột B>  Thứ tự hàng trong file quyết định thống kê min/max của mỗi
                    row group có ích hay vô dụng. Sắp thế nào để các hàng cùng
                    một khách hàng nằm liền nhau?

  ROW_GROUP_SIZE    Mặc định 122.880 hàng. Một ngày có khoảng bao nhiêu hàng?
                    Nếu cả ngày gói gọn trong MỘT row group thì min/max của
                    row group đó phủ những gì, và còn tác dụng lọc không?

Sau khi chạy xong, kiểm tra lại bằng `python tools/explain.py`: `rows scanned`
phải giảm, `files` phải giảm, và `result hash` phải GIỮ NGUYÊN.
"""

from __future__ import annotations

import pathlib
import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from tools.common import DATA  # noqa: E402

SRC = DATA / "gold_events"
DST = DATA / "gold_events_v2"


# ---------------------------------------------------------------- quyết định
#
# PARTITION_BY (event_date)
#   Dashboard lọc theo hai cột: event_date (ngày) và customer_name (khách).
#   Chỉ một trong hai được đưa vào đường dẫn — cột kia phải giải quyết bằng
#   thống kê row group. Chọn event_date vì nó có 14 giá trị phân biệt => 14
#   thư mục, mỗi thư mục ~9.300 hàng: đủ lớn để file không vụn trở lại.
#   Partition theo customer_name (650 giá trị) sẽ tái tạo đúng small-file
#   problem đang phải sửa: 650 thư mục × 14 ngày = 9.100 file tí hon.
#
# ORDER BY (customer_name, event_time)
#   Thứ tự hàng quyết định min/max của từng row group có ích hay vô dụng.
#   Sắp theo customer_name trước => hàng của một khách nằm liền nhau, chỉ vài
#   row group có khoảng [min, max] chứa 'ACME'; các row group còn lại bị loại
#   mà không cần giải nén. event_time là khoá phụ, giữ dữ liệu trong ngày theo
#   trình tự thời gian cho các truy vấn khác.
#
# ROW_GROUP_SIZE = 2048
#   Mặc định 122.880 hàng > số hàng của cả một ngày => cả ngày gói trong MỘT
#   row group, min/max của nó trải từ 'ACME' tới 'Cust_0650' nên không loại
#   được gì. 2.048 hàng cho ~5 row group mỗi ngày: đủ nhỏ để lọc theo
#   customer_name có tác dụng, đủ lớn để không phình metadata.
PARTITION_COL = "event_date"
SORT_COLS = ("customer_name", "event_time")
ROW_GROUP_SIZE = 2048


def main() -> int:
    con = duckdb.connect()
    con.execute("set threads to 4")

    n_src = len(list(SRC.glob("*.parquet")))
    print(f"  nguồn : {SRC}  ({n_src:,} file)")

    rows_src = con.execute(
        f"select count(*) from read_parquet('{SRC}/*.parquet')"
    ).fetchone()[0]

    con.execute(f"""
        copy (
            select * from read_parquet('{SRC}/*.parquet')
            order by {", ".join(SORT_COLS)}
        ) to '{DST}' (
            format          parquet,
            partition_by    ({PARTITION_COL}),
            overwrite_or_ignore,
            row_group_size  {ROW_GROUP_SIZE}
        )
    """)

    rows_dst = con.execute(
        f"select count(*) from read_parquet('{DST}/**/*.parquet', hive_partitioning = true)"
    ).fetchone()[0]
    n_dst = len(list(DST.rglob("*.parquet")))

    assert rows_src == rows_dst, f"mất hàng: {rows_src:,} -> {rows_dst:,}"

    print(f"  đích  : {DST}  ({n_dst:,} file, partition theo {PARTITION_COL})")
    print(f"  hàng  : {rows_src:,} -> {rows_dst:,}  (không mất hàng nào)")
    print(f"  layout: order by {', '.join(SORT_COLS)} · row_group_size {ROW_GROUP_SIZE:,}")
    print("\n  đo lại bằng:  make explain\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
