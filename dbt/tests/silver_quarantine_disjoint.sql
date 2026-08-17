-- Test mới (nhiệm vụ 3): silver_tickets và quarantine_tickets phải là hai
-- tập RỜI NHAU trên cùng một bản ghi CDC — không bản ghi nào vừa được nhận
-- vào Silver vừa bị quarantine, và không bản ghi hỏng nào bị bỏ quên ở giữa.
--
-- Cả hai model gọi chung macro normalize_priority nên điều kiện luôn là phủ
-- định của nhau; test này khoá lại tính chất đó để lần sau ai sửa một bên mà
-- quên bên kia thì dbt test đỏ ngay.

with cdc as (
    select
        ticket_id,
        cdc_seq,
        {{ normalize_priority('priority_raw') }} as priority_clean
    from {{ source('bronze', 'bronze_tickets_cdc') }}
),

quarantined as (
    select ticket_id, cdc_seq from {{ ref('quarantine_tickets') }}
)

select c.ticket_id, c.cdc_seq
from cdc c
left join quarantined q
  on q.ticket_id = c.ticket_id and q.cdc_seq = c.cdc_seq
where (c.priority_clean is null) <> (q.ticket_id is not null)
