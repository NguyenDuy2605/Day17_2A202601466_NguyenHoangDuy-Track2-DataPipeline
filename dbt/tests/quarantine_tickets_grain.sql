-- Test mới (nhiệm vụ 3): quarantine_tickets có grain 1 hàng / 1 BẢN GHI CDC.
-- Một ticket có nhiều bản ghi CDC, nên ticket_id một mình KHÔNG phải khoá;
-- khoá là (ticket_id, cdc_seq). Test fail nếu bảng bị nhân bản hoặc bị gộp
-- nhầm về grain ticket.

select
    ticket_id,
    cdc_seq,
    count(*) as n
from {{ ref('quarantine_tickets') }}
group by 1, 2
having count(*) > 1
