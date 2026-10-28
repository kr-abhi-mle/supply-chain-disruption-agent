# Disruption impact report

**Query:** Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days

**Run mode:** offline

## How the system understood this

A weather disruption delays freight leaving the state of Sao Paulo (SP) by 5 days.

| type | place | direction | delay_days | product_focus |
|---|---|---|---|---|
| weather | SP | outbound | 5 | heavy bulky items such as furniture and home goods |

**Assumptions:**

- 'Sao Paulo' read as the state SP. Say 'city of Sao Paulo' to mean the city.
- No product focus given: ranked 'heavy bulky items such as furniture and home goods' first

## Executive summary

_Written by: Template._

A weather disruption delays freight leaving the state of Sao Paulo (SP) by 5 days. It affects 7,037 orders (7,959 items) from 922 sellers. 2,268 orders (32.2%) will now miss their promised date, on average by 4.2 days; 358 are CRITICAL and 1,186 HIGH. The rules reroute 1,389 orders, delay 820 with compensation and offer cancellation on 59, while 4,769 need no action. Late orders are worth R$ 241,748.63, and the estimated compensation cost is R$ 36,976.82. The most affected categories are bed bath table, health beauty, housewares.

## Recommended next steps

_For the operations team. Written by: Template._

- Contact the most affected sellers first about pickups and stock: seller 6560211a in sao paulo, SP (321 orders), seller 1025f0e2 in sao paulo, SP (176 orders), seller 4869f7a5 in guariba, SP (124 orders).
- Book expedited capacity on unaffected routes for 1,389 reroutes, which cuts their average delay from 5.5 to 2.5 days at an estimated R$ 20,033.15.
- Arrange special carriers for 96 bulky orders that will wait, and refund their freight (R$ 4,784.50 in total).
- Confirm the 59 cancellations with customers; full refunds total R$ 5,167.21.
- Review the 429 orders flagged for human review before their emails go out.

## Headline numbers

| affected orders | items | sellers | customers | late | value at risk | compensation |
|---|---|---|---|---|---|---|
| 7,037 | 7,959 | 922 | 7,037 | 32.2% | R$ 241,748.63 | R$ 36,976.82 |

## Orders by severity

| severity | orders |
|---|---|
| LOW | 4769 |
| MEDIUM | 724 |
| HIGH | 1186 |
| CRITICAL | 358 |

## Mitigation plan

Rules are checked in order R0 to R4, and the first match decides the action. Every order's rule and reasons are in `orders.csv`.

| rule | action | when | customer offer | orders | avg days late if no action | avg days late after action | cost (R$) |
|---|---|---|---|---|---|---|---|
| R0 | MONITOR | Severity LOW: the delivery buffer absorbs the delay | None needed, no email | 4769 | 0.0 | 0.0 | 0.0 |
| R1 | CANCEL | Time-sensitive item and severity HIGH or CRITICAL | Free cancellation with a full refund | 59 | 4.8 | n/a | 5167.21 |
| R2 | DELAY | Bulky item (expensive and slow to reroute) | Freight charge refunded | 96 | 5.1 | 5.1 | 4784.5 |
| R3 | REROUTE | Severity HIGH or CRITICAL, small item | Free expedited shipping, 2 extra days instead of the full delay | 1389 | 5.5 | 2.5 | 20033.15 |
| R4 | DELAY | Anything else (severity MEDIUM) | 10% voucher for the next order | 724 | 1.5 | 1.5 | 6991.96 |

## Orders flagged for human review

429 orders were flagged by code. The most important are below. Flags never change a decision. Notes written by: Template.

| order | rule | action | severity | note |
|---|---|---|---|---|
| f92d5a62 | R3 | REROUTE | CRITICAL | Already 10 days late before the disruption; still 12 days late after rerouting; high-value order (R$ 699.00). The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated, whether a faster carrier is available and that the standard compensation is enough for this customer. |
| 1b0bc119 | R2 | DELAY | CRITICAL | High-value order (R$ 1,467.80); 3 affected items from 2 sellers. The R2 DELAY decision stands. Check that the standard compensation is enough for this customer and whether the items should ship separately. |
| 28e5c316 | R1 | CANCEL | CRITICAL | Both bulky and time-sensitive, so the cancellation rule R1 took priority over R2. The R1 CANCEL decision stands. Check that cancelling is better than a late delivery. |
| bd429f27 | R3 | REROUTE | CRITICAL | Already 7 days late before the disruption; still 9 days late after rerouting; high-value order (R$ 699.42). The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated, whether a faster carrier is available and that the standard compensation is enough for this customer. |
| db747e7d | R3 | REROUTE | CRITICAL | Already 7 days late before the disruption; still 9 days late after rerouting; high-value order (R$ 966.90). The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated, whether a faster carrier is available and that the standard compensation is enough for this customer. |

## Priority products

| product | category | weight_kg | volume_l | severity | why |
|---|---|---|---|---|---|
| ada6a911 | home_appliances_2 | 14.8 | 56 | CRITICAL | bulky and 20 days late |
| 613221d7 | office_furniture | 22.7 | 49 | CRITICAL | bulky and 18 days late; matches the product focus |
| 581de99f | baby | 13.8 | 81 | CRITICAL | bulky and 17 days late |
| 84777fa5 | furniture_decor | 10.7 | 64 | CRITICAL | bulky and 17 days late |
| f0f34793 | furniture_decor | 25.3 | 152 | CRITICAL | bulky and 14 days late |
| 0ec7b6a8 | bed_bath_table | 7.5 | 63 | CRITICAL | bulky and 13 days late |
| 0d8c593f | housewares | 28.2 | 178 | CRITICAL | bulky and 12 days late |
| db99498f | office_furniture | 17.9 | 108 | CRITICAL | bulky and 11 days late |
| a5647c44 | office_furniture | 12.2 | 80 | CRITICAL | bulky and 6 days late; matches the product focus |
| 914c9e9a | office_furniture | 7.5 | 125 | CRITICAL | bulky and 6 days late; matches the product focus |
| b98992ea | kitchen_dining_laundry_garden_furniture | 10.4 | 35 | CRITICAL | bulky and 5 days late; matches the product focus |
| da501879 | office_furniture | 22.6 | 38 | CRITICAL | bulky and 5 days late; matches the product focus |
| 2a5806f1 | office_furniture | 11.9 | 69 | CRITICAL | bulky and 5 days late; matches the product focus |
| b114bf33 | office_furniture | 13.3 | 70 | CRITICAL | bulky and 4 days late; matches the product focus |

## Most affected sellers

| seller | location | items | orders |
|---|---|---|---|
| 6560211a | sao paulo, SP | 349 | 321 |
| 1025f0e2 | sao paulo, SP | 246 | 176 |
| 4869f7a5 | guariba, SP | 127 | 124 |
| 9f505651 | sao paulo, SP | 114 | 108 |
| e9779976 | praia grande, SP | 112 | 91 |

## Most affected categories

| category | items | late_items |
|---|---|---|
| bed_bath_table | 856 | 262 |
| health_beauty | 817 | 270 |
| housewares | 670 | 236 |
| watches_gifts | 607 | 157 |
| sports_leisure | 503 | 147 |

## Sample customer emails

### CANCEL: Your order 28e5c316: free cancellation and full refund

_Written by: Template. Order 28e5c316b9b1b1902c094ab90ea33ffd._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting freight leaving Sao Paulo, your order 28e5c316 (food drink, bought on 23 August 2018) cannot reach Sumare, SP in time. These items lose their value when they arrive late, so we would rather not keep you waiting.
>
> You can cancel at no cost and receive a full refund of R$ 147.62.
>
> Reply to this email to confirm the cancellation, or to keep the order if you still want it.
>
> Thank you for your patience,
> Customer Care Team

### REROUTE: Your order 00063b38 is on a faster route

_Written by: Template. Order 00063b381e2406b52ad429470734ebd5._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting freight leaving Sao Paulo, your order 00063b38 (fashion bags accessories, bought on 27 July 2018) was at risk of missing its promised date of 7 August 2018.
>
> We have moved it to an unaffected route with free expedited shipping, at no cost to you. It should now arrive in Monte Alto, SP by 9 August 2018.
>
> You do not need to do anything. The new route is already booked.
>
> Thank you for your patience,
> Customer Care Team

### DELAY: Your order 1b0bc119 is delayed, and your freight is refunded

_Written by: Template. Order 1b0bc119ea5ac37e73e2275afc7904ee._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting freight leaving Sao Paulo, your order 1b0bc119 (computers and furniture decor, bought on 14 August 2018) will miss its promised date of 23 August 2018. Large items like yours need special carriers, so we are keeping it on its current route.
>
> It should now arrive in Sao Paulo, SP by 28 August 2018. To make up for the wait, we have refunded your freight charge of R$ 75.45.
>
> You do not need to do anything. The refund is automatic.
>
> Thank you for your patience,
> Customer Care Team

## One order traced end to end

Order `28e5c316b9b1b1902c094ab90ea33ffd`

- **Item:** food_drink, 10.5 kg, 28 L, seller praia grande/SP to customer sumare/SP
- **Retrieval:** filter {'seller_state': {'$in': ['SP']}}
- **Logistics:** baseline ETA 2018-08-29, promised 2018-08-31, new ETA 2018-09-03
- **Logistics:** Buffer 2 days, delay 5 days, so 3 days late: HIGH
- **Logistics:** Bulky (10.5 kg, 28 L): raised to CRITICAL
- **Decision:** R1 CANCEL: Free cancellation with a full refund of R$ 147.62. Time-sensitive goods lose their value when 3 days late, so refund instead
- **Email:** Your order 28e5c316: free cancellation and full refund

## Step trace

| step | count | ms | detail |
|---|---|---|---|
| 1. Parse disruption | 0 | 51 | A weather disruption delays freight leaving the state of Sao Paulo (SP) by 5 days. (parsed by rules) |
| 2. Retrieve affected items | 7959 | 461 | filter {'seller_state': {'$in': ['SP']}}; 50 best matches for 'heavy bulky items such as furniture and home goods' |
| 3. Analyse impact | 7037 | 62 | 2268 of 7037 orders become late |
| 4. Decide actions | 7037 | 10 | rules R0 to R4, first match wins |
| 5. Write customer emails | 3 | 2 | written by template |
| 6. Write report | 0 | 22 | Gemini calls 0, tokens 0 |

**LLM notes:**

- No step fell back.
