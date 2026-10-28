# Disruption impact report

**Query:** Truckers' strike in Curitiba, shipments out of the city stuck for a week

**Run mode:** gemini (gemini-3.5-flash-lite)

## How the system understood this

A strike disruption delays freight leaving the city of Curitiba by 7 days.

| type | place | direction | delay_days | product_focus |
|---|---|---|---|---|
| strike | curitiba | outbound | 7 | heavy bulky items such as furniture and home goods |

**Assumptions:**

- No product focus given: ranked 'heavy bulky items such as furniture and home goods' first

## Executive summary

_Written by: Gemini._

A strike disruption delays freight leaving the city of Curitiba by 7 days, hitting 301 orders and 57 sellers. A total of 79 orders will be late, with an average delay of 4.3 days. The incident affects 301 customers and 320 items across categories including furniture decor, housewares, and sports leisure. The decision rules allocated 222 orders to monitor, 6 to delay with freight refunded, 42 to reroute with free expedited shipping, and 31 to delay with a 10% voucher. The estimated compensation cost totals R$ 1,569.57 for late orders valued at R$ 14,223.58.

## Recommended next steps

_For the operations team. Written by: Gemini._

- Contact sellers 0241d4d5, 77530e97, and 671585f5 first because they are the most affected in Curitiba, PR.
- Book extra carrier capacity where needed to support the 42 rerouted orders and minimize further delays.
- Prepare for customer communications regarding refunds and cancellations as outlined in the mitigation plan.
- Review the 8 orders flagged for human review in the queue to handle critical cases appropriately.

## Headline numbers

| affected orders | items | sellers | customers | late | value at risk | compensation |
|---|---|---|---|---|---|---|
| 301 | 320 | 57 | 301 | 26.2% | R$ 14,223.58 | R$ 1,569.57 |

## Orders by severity

| severity | orders |
|---|---|
| LOW | 222 |
| MEDIUM | 31 |
| HIGH | 38 |
| CRITICAL | 10 |

## Mitigation plan

Rules are checked in order R0 to R4, and the first match decides the action. Every order's rule and reasons are in `orders.csv`.

| rule | action | when | customer offer | orders | avg days late if no action | avg days late after action | cost (R$) |
|---|---|---|---|---|---|---|---|
| R0 | MONITOR | Severity LOW: the delivery buffer absorbs the delay | None needed, no email | 222 | 0.0 | 0.0 | 0.0 |
| R1 | CANCEL | Time-sensitive item and severity HIGH or CRITICAL | Free cancellation with a full refund | 0 | 0 | n/a | 0 |
| R2 | DELAY | Bulky item (expensive and slow to reroute) | Freight charge refunded | 6 | 4.3 | 4.3 | 309.9 |
| R3 | REROUTE | Severity HIGH or CRITICAL, small item | Free expedited shipping, 2 extra days instead of the full delay | 42 | 6.4 | 2.2 | 851.85 |
| R4 | DELAY | Anything else (severity MEDIUM) | 10% voucher for the next order | 31 | 1.5 | 1.5 | 407.82 |

## Orders flagged for human review

8 orders were flagged by code. The most important are below. Flags never change a decision. Notes written by: Gemini.

| order | rule | action | severity | note |
|---|---|---|---|---|
| b2997e1d | R3 | REROUTE | CRITICAL | This critical severity order was already 49 days late before the disruption and remains 51 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 4160b644 | R2 | DELAY | CRITICAL | This critical severity order involves a high-value amount of R$ 2,999.90. Check that the standard compensation is enough for this customer. |
| 4cf09d9e | R3 | REROUTE | CRITICAL | This critical severity order was already 11 days late before the disruption and remains 13 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 8d041d79 | R3 | REROUTE | CRITICAL | This critical severity order was already 7 days late before the disruption and remains 9 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 99712096 | R2 | DELAY | CRITICAL | This critical severity order was already 6 days late before the disruption. Check whether the customer has already complained or been compensated. |

## Priority products

| product | category | weight_kg | volume_l | severity | why |
|---|---|---|---|---|---|
| 741e14d6 | baby | 1.4 | 60 | CRITICAL | bulky and 13 days late |
| cc1829ca | sports_leisure | 7.9 | 60 | CRITICAL | bulky and 6 days late |
| c2fb73db | baby | 3.6 | 60 | CRITICAL | bulky and 3 days late |
| 2b4472df | kitchen_dining_laundry_garden_furniture | 13.6 | 115 | HIGH | bulky and 2 days late; matches the product focus |
| 5b3b5f9a | toys | 5.4 | 60 | HIGH | bulky and 1 days late |
| 78efe838 | furniture_decor | 2.5 | 12 | CRITICAL | matches the product focus |
| b10ecf8e | furniture_decor | 2.3 | 22 | HIGH | matches the product focus |
| 3e845176 | furniture_decor | 1.6 | 7 | HIGH | matches the product focus |
| d03bd02a | furniture_decor | 1.8 | 12 | HIGH | matches the product focus |

## Most affected sellers

| seller | location | items | orders |
|---|---|---|---|
| 0241d4d5 | curitiba, PR | 50 | 49 |
| 77530e97 | curitiba, PR | 33 | 26 |
| 671585f5 | curitiba, PR | 27 | 27 |
| c3cfdc64 | curitiba, PR | 20 | 20 |
| ccc4bbb5 | curitiba, PR | 17 | 17 |

## Most affected categories

| category | items | late_items |
|---|---|---|
| furniture_decor | 86 | 32 |
| housewares | 55 | 6 |
| sports_leisure | 49 | 17 |
| health_beauty | 26 | 4 |
| auto | 14 | 0 |

## Sample customer emails

### REROUTE: Update on your order 0f44fd64

_Written by: Gemini. Order 0f44fd64ee902f504aefed510fbcb8e7._

> Hello,
>
> We sincerely apologize for the delay in delivering your furniture decor purchased on 10 August 2018, which was originally promised by 20 August 2018.
>
> Your order has been affected by a transport strike affecting freight leaving Curitiba. To resolve this, we are providing free expedited shipping through an unaffected route, and your new delivery date is 22 August 2018.
>
> You do not need to do anything. The new route is already booked.
>
> Thank you for your patience,
> Customer Care Team

### DELAY: Update on your order 4160b644

_Written by: Gemini. Order 4160b6447ad70e6d73f7221dd970bbe9._

> Hello,
>
> We sincerely apologize for the delay with your sports leisure order purchased on 15 August 2018 and originally promised for delivery by 31 August 2018. This delay was caused by a transport strike affecting freight leaving Curitiba.
>
> The new delivery date is 6 September 2018, and as a resolution, your freight charge of R$ 76.23 has been refunded.
>
> You do not need to do anything. The refund is automatic.
>
> Thank you for your patience,
> Customer Care Team

## One order traced end to end

Order `0f44fd64ee902f504aefed510fbcb8e7`

- **Item:** furniture_decor, 0.3 kg, 8 L, seller curitiba/PR to customer sao mateus do sul/PR
- **Retrieval:** filter {'seller_city': {'$in': ['curitiba']}}
- **Logistics:** baseline ETA 2018-08-20, promised 2018-08-20, new ETA 2018-08-27
- **Logistics:** Buffer 0 days, delay 7 days, so 7 days late: CRITICAL
- **Decision:** R3 REROUTE: Free expedited shipping through an unaffected route. Small goods move easily by another carrier: 2 extra days instead of 7
- **Email:** Update on your order 0f44fd64

## Step trace

| step | count | ms | detail |
|---|---|---|---|
| 1. Parse disruption | 0 | 2579 | A strike disruption delays freight leaving the city of Curitiba by 7 days. (parsed by gemini) |
| 2. Retrieve affected items | 320 | 379 | filter {'seller_city': {'$in': ['curitiba']}}; 50 best matches for 'heavy bulky items such as furniture and home goods' |
| 3. Analyse impact | 301 | 1 | 79 of 301 orders become late |
| 4. Decide actions | 301 | 0 | rules R0 to R4, first match wins |
| 5. Write customer emails | 2 | 2514 | written by gemini |
| 6. Write report | 0 | 2035 | Gemini calls 4, tokens 2936 |

**LLM notes:**

- gemini-3.6-flash was unavailable (gemini-3.6-flash: HTTP 429), so gemini-3.5-flash-lite answered
