# Disruption impact report

**Query:** Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days

**Run mode:** offline

## How the system understood this

A weather disruption delays deliveries into the state of Rio Grande do Sul (RS) by 10 days.

| type | place | direction | delay_days | product_focus |
|---|---|---|---|---|
| weather | RS | inbound | 10 | heavy bulky items such as furniture and home goods |

**Assumptions:**

- No product focus given: ranked 'heavy bulky items such as furniture and home goods' first

## Executive summary

_Written by: Template._

A weather disruption delays deliveries into the state of Rio Grande do Sul (RS) by 10 days. It affects 466 orders (571 items) from 297 sellers. 196 orders (42.1%) will now miss their promised date, on average by 5.3 days; 72 are CRITICAL and 82 HIGH. The rules reroute 142 orders, delay 51 with compensation and offer cancellation on 3, while 270 need no action. Late orders are worth R$ 28,582.71, and the estimated compensation cost is R$ 5,317.61. The most affected categories are housewares, furniture decor, health beauty.

## Recommended next steps

_For the operations team. Written by: Template._

- Contact the most affected sellers first about pickups and stock: seller 1025f0e2 in sao paulo, SP (16 orders), seller 53243585 in lauro de freitas, BA (5 orders), seller 612170e3 in novo hamburgo, RS (11 orders).
- Book expedited capacity on unaffected routes for 142 reroutes, which cuts their average delay from 6.2 to 0.7 days at an estimated R$ 3,755.93.
- Arrange special carriers for 9 bulky orders that will wait, and refund their freight (R$ 668.21 in total).
- Confirm the 3 cancellations with customers; full refunds total R$ 294.24.
- Review the 19 orders flagged for human review before their emails go out.

## Headline numbers

| affected orders | items | sellers | customers | late | value at risk | compensation |
|---|---|---|---|---|---|---|
| 466 | 571 | 297 | 466 | 42.1% | R$ 28,582.71 | R$ 5,317.61 |

## Orders by severity

| severity | orders |
|---|---|
| LOW | 270 |
| MEDIUM | 42 |
| HIGH | 82 |
| CRITICAL | 72 |

## Mitigation plan

Rules are checked in order R0 to R4, and the first match decides the action. Every order's rule and reasons are in `orders.csv`.

| rule | action | when | customer offer | orders | avg days late if no action | avg days late after action | cost (R$) |
|---|---|---|---|---|---|---|---|
| R0 | MONITOR | Severity LOW: the delivery buffer absorbs the delay | None needed, no email | 270 | 0.0 | 0.0 | 0.0 |
| R1 | CANCEL | Time-sensitive item and severity HIGH or CRITICAL | Free cancellation with a full refund | 3 | 6.0 | n/a | 294.24 |
| R2 | DELAY | Bulky item (expensive and slow to reroute) | Freight charge refunded | 9 | 8.9 | 8.9 | 668.21 |
| R3 | REROUTE | Severity HIGH or CRITICAL, small item | Free expedited shipping, 2 extra days instead of the full delay | 142 | 6.2 | 0.7 | 3755.93 |
| R4 | DELAY | Anything else (severity MEDIUM) | 10% voucher for the next order | 42 | 1.5 | 1.5 | 599.23 |

## Orders flagged for human review

19 orders were flagged by code. The most important are below. Flags never change a decision. Notes written by: Template.

| order | rule | action | severity | note |
|---|---|---|---|---|
| 734e6635 | R3 | REROUTE | CRITICAL | Already 17 days late before the disruption; still 19 days late after rerouting. The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated and whether a faster carrier is available. |
| 6d0940a8 | R2 | DELAY | CRITICAL | Already 15 days late before the disruption; high-value order (R$ 2,350.00). The R2 DELAY decision stands. Check whether the customer has already complained or been compensated and that the standard compensation is enough for this customer. |
| ad1c31ec | R3 | REROUTE | HIGH | 2 affected items from 2 sellers. The R3 REROUTE decision stands. Check whether the items should ship separately. |
| 758480e1 | R3 | REROUTE | CRITICAL | Already 7 days late before the disruption; still 9 days late after rerouting. The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated and whether a faster carrier is available. |
| 828999d8 | R3 | REROUTE | CRITICAL | Already 6 days late before the disruption; still 8 days late after rerouting. The R3 REROUTE decision stands. Check whether the customer has already complained or been compensated and whether a faster carrier is available. |

## Priority products

| product | category | weight_kg | volume_l | severity | why |
|---|---|---|---|---|---|
| ada6a911 | home_appliances_2 | 14.8 | 56 | CRITICAL | bulky and 25 days late; matches the product focus |
| 741e14d6 | baby | 1.4 | 60 | CRITICAL | bulky and 16 days late |
| 0f6aa686 | housewares | 10.4 | 40 | CRITICAL | bulky and 11 days late; matches the product focus |
| 66e94c5c | agro_industry_and_commerce | 12.7 | 57 | CRITICAL | bulky and 9 days late |
| f8763c8e | bed_bath_table | 20.3 | 139 | CRITICAL | bulky and 5 days late; matches the product focus |
| 813a3005 | health_beauty | 12.0 | 78 | CRITICAL | bulky and 5 days late |
| db96ef2a | agro_industry_and_commerce | 12.4 | 56 | CRITICAL | bulky and 5 days late |
| 7814c273 | furniture_decor | 12.2 | 71 | HIGH | bulky and 2 days late; matches the product focus |
| 5d6bea33 | furniture_decor | 4.0 | 32 | CRITICAL | matches the product focus |
| 18f6ea7e | kitchen_dining_laundry_garden_furniture | 1.9 | 24 | CRITICAL | matches the product focus |
| a6ad77b1 | furniture_decor | 3.5 | 28 | CRITICAL | matches the product focus |
| 2216232c | housewares | 6.8 | 32 | CRITICAL | matches the product focus |
| 78efe838 | furniture_decor | 2.5 | 12 | HIGH | matches the product focus |
| 081cac4f | home_appliances | 0.1 | 2 | HIGH | matches the product focus |
| 7a5d0e89 | housewares | 2.2 | 11 | HIGH | matches the product focus |

## Most affected sellers

| seller | location | items | orders |
|---|---|---|---|
| 1025f0e2 | sao paulo, SP | 26 | 16 |
| 53243585 | lauro de freitas, BA | 25 | 5 |
| 612170e3 | novo hamburgo, RS | 11 | 11 |
| 6560211a | sao paulo, SP | 10 | 9 |
| ea8482cd | sao paulo, SP | 7 | 7 |

## Most affected categories

| category | items | late_items |
|---|---|---|
| housewares | 66 | 30 |
| furniture_decor | 53 | 17 |
| health_beauty | 46 | 17 |
| telephony | 45 | 26 |
| bed_bath_table | 43 | 16 |

## Sample customer emails

### CANCEL: Your order 2d3b53a5: free cancellation and full refund

_Written by: Template. Order 2d3b53a594f674cb7c476510f364c430._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting deliveries into Rio Grande do Sul, your order 2d3b53a5 (food, bought on 26 July 2018) cannot reach Porto Alegre, RS in time. These items lose their value when they arrive late, so we would rather not keep you waiting.
>
> You can cancel at no cost and receive a full refund of R$ 92.40.
>
> Reply to this email to confirm the cancellation, or to keep the order if you still want it.
>
> Thank you for your patience,
> Customer Care Team

### REROUTE: Your order 51d70226 is on a faster route

_Written by: Template. Order 51d70226d271148b34f0ae2a6aaef7e8._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting deliveries into Rio Grande do Sul, your order 51d70226 (furniture decor and home construction, bought on 6 August 2018) was at risk of missing its promised date of 17 August 2018.
>
> We have moved it to an unaffected route with free expedited shipping, at no cost to you. It should now arrive in Porto Alegre, RS by 19 August 2018.
>
> You do not need to do anything. The new route is already booked.
>
> Thank you for your patience,
> Customer Care Team

### DELAY: Your order fdff9465 is delayed, and your freight is refunded

_Written by: Template. Order fdff9465ac9ce1a793bb30fa94c6f241._

> Hello,
>
> We are sorry for the trouble with your order. Because of severe weather affecting deliveries into Rio Grande do Sul, your order fdff9465 (agro industry and commerce, bought on 29 July 2018) will miss its promised date of 8 August 2018. Large items like yours need special carriers, so we are keeping it on its current route.
>
> It should now arrive in Dois Irmaos, RS by 17 August 2018. To make up for the wait, we have refunded your freight charge of R$ 27.63.
>
> You do not need to do anything. The refund is automatic.
>
> Thank you for your patience,
> Customer Care Team

## One order traced end to end

Order `2d3b53a594f674cb7c476510f364c430`

- **Item:** food, 0.1 kg, 3 L, seller atibaia/SP to customer porto alegre/RS
- **Item:** food, 0.1 kg, 3 L, seller atibaia/SP to customer porto alegre/RS
- **Retrieval:** filter {'customer_state': {'$in': ['RS']}}
- **Logistics:** baseline ETA 2018-08-13, promised 2018-08-16, new ETA 2018-08-23
- **Logistics:** 2 affected items; the worst (food) sets the order severity
- **Logistics:** Buffer 3 days, delay 10 days, so 7 days late: CRITICAL
- **Decision:** R1 CANCEL: Free cancellation with a full refund of R$ 92.40. Time-sensitive goods lose their value when 7 days late, so refund instead
- **Email:** Your order 2d3b53a5: free cancellation and full refund

## Step trace

| step | count | ms | detail |
|---|---|---|---|
| 1. Parse disruption | 0 | 50 | A weather disruption delays deliveries into the state of Rio Grande do Sul (RS) by 10 days. (parsed by rules) |
| 2. Retrieve affected items | 571 | 162 | filter {'customer_state': {'$in': ['RS']}}; 50 best matches for 'heavy bulky items such as furniture and home goods' |
| 3. Analyse impact | 466 | 3 | 196 of 466 orders become late |
| 4. Decide actions | 466 | 0 | rules R0 to R4, first match wins |
| 5. Write customer emails | 3 | 0 | written by template |
| 6. Write report | 0 | 1 | Gemini calls 0, tokens 0 |

**LLM notes:**

- No step fell back.
