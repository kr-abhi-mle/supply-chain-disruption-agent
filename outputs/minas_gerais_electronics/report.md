# Disruption impact report

**Query:** Heavy rains in Minas Gerais are delaying electronics and computer shipments leaving the state for 4 days

**Run mode:** gemini (gemini-3.5-flash-lite)

## How the system understood this

A weather disruption delays freight leaving the state of Minas Gerais (MG) by 4 days.

| type | place | direction | delay_days | product_focus |
|---|---|---|---|---|
| weather | MG | outbound | 4 | electronics and computer shipments |

**Assumptions:**

- None

## Executive summary

_Written by: Gemini._

A weather disruption delays freight leaving the state of Minas Gerais (MG) by 4 days, impacting 678 orders, 731 items, 110 sellers, and 678 customers. Out of these, 87 orders are late, representing 12.8% of the total, and will be late on average by 3.2 days. The most affected categories are computers accessories, housewares, and pet shop. The rules decided to monitor 591 orders, delay 48 orders, reroute 39 orders, and cancel 0 orders. The estimated compensation cost for these disruptions is R$ 1,647.24, with the total value of late orders reaching R$ 10,341.00.

## Recommended next steps

_For the operations team. Written by: Gemini._

- Contact seller 85d9eb9d, seller a1043baf, and seller acce39e8 first since they have the most affected orders.
- Book extra carrier capacity where needed to support the rerouted shipments and mitigate further delays.
- Prepare for any potential refunds and cancellations as flagged by the review process.
- Review the human review queue thoroughly to address critical and high-severity orders.

## Headline numbers

| affected orders | items | sellers | customers | late | value at risk | compensation |
|---|---|---|---|---|---|---|
| 678 | 731 | 110 | 678 | 12.8% | R$ 10,341.00 | R$ 1,647.24 |

## Orders by severity

| severity | orders |
|---|---|
| LOW | 591 |
| MEDIUM | 44 |
| HIGH | 36 |
| CRITICAL | 7 |

## Mitigation plan

Rules are checked in order R0 to R4, and the first match decides the action. Every order's rule and reasons are in `orders.csv`.

| rule | action | when | customer offer | orders | avg days late if no action | avg days late after action | cost (R$) |
|---|---|---|---|---|---|---|---|
| R0 | MONITOR | Severity LOW: the delivery buffer absorbs the delay | None needed, no email | 591 | 0.0 | 0.0 | 0.0 |
| R1 | CANCEL | Time-sensitive item and severity HIGH or CRITICAL | Free cancellation with a full refund | 0 | 0 | n/a | 0 |
| R2 | DELAY | Bulky item (expensive and slow to reroute) | Freight charge refunded | 4 | 3.0 | 3.0 | 301.52 |
| R3 | REROUTE | Severity HIGH or CRITICAL, small item | Free expedited shipping, 2 extra days instead of the full delay | 39 | 5.2 | 3.2 | 855.48 |
| R4 | DELAY | Anything else (severity MEDIUM) | 10% voucher for the next order | 44 | 1.4 | 1.4 | 490.24 |

## Orders flagged for human review

10 orders were flagged by code. The most important are below. Flags never change a decision. Notes written by: Gemini.

| order | rule | action | severity | note |
|---|---|---|---|---|
| 238652e3 | R3 | REROUTE | CRITICAL | This order has a CRITICAL severity and was already 38 days late before the disruption, remaining 40 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 059162a0 | R2 | DELAY | HIGH | This order has a HIGH severity and is a high-value order worth R$ 839.99. Check that the standard compensation is enough for this customer. |
| 0a92bad7 | R3 | REROUTE | CRITICAL | This order has a CRITICAL severity and was already 11 days late before the disruption, remaining 13 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 5aa65dc2 | R3 | REROUTE | CRITICAL | This order has a CRITICAL severity and was already 4 days late before the disruption, remaining 6 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |
| 11526907 | R3 | REROUTE | CRITICAL | This order has a CRITICAL severity and was already 3 days late before the disruption, remaining 5 days late after rerouting. Check whether the customer has already complained or been compensated, and whether a faster carrier is available. |

## Priority products

| product | category | weight_kg | volume_l | severity | why |
|---|---|---|---|---|---|
| 4e191b1e | home_confort | 2.4 | 77 | CRITICAL | bulky and 5 days late |
| 4b967866 | housewares | 10.8 | 59 | CRITICAL | bulky and 4 days late |
| 1e291c0c | luggage_accessories | 9.6 | 75 | HIGH | bulky and 2 days late |
| 90c1b4e0 | furniture_living_room | 30.0 | 294 | HIGH | bulky and 1 days late |
| 18b0e642 | computers_accessories | 0.2 | 2 | HIGH | matches the product focus |
| 1af2a3ec | computers_accessories | 0.1 | 2 | MEDIUM | matches the product focus |
| a783f0d7 | computers_accessories | 0.2 | 2 | LOW | matches the product focus |
| d1c42706 | computers_accessories | 6.5 | 8 | LOW | matches the product focus |
| 34194988 | computers_accessories | 0.1 | 8 | LOW | matches the product focus |
| b8eb8663 | computers_accessories | 0.4 | 2 | LOW | matches the product focus |

## Most affected sellers

| seller | location | items | orders |
|---|---|---|---|
| 85d9eb9d | belo horizonte, MG | 55 | 55 |
| a1043baf | ilicinea, MG | 43 | 42 |
| acce39e8 | contagem, MG | 35 | 35 |
| 7299e27e | araguari, MG | 34 | 33 |
| dbc22125 | borda da mata, MG | 30 | 30 |

## Most affected categories

| category | items | late_items |
|---|---|---|
| computers_accessories | 100 | 6 |
| housewares | 75 | 8 |
| pet_shop | 56 | 17 |
| stationery | 46 | 5 |
| health_beauty | 43 | 5 |

## Sample customer emails

### REROUTE: Update on your order 14a05c02

_Written by: Gemini. Order 14a05c02d483800864e5c19a3a7f0ee2._

> Hello,
>
> We sincerely apologize for the delay with your order purchased on 18 August 2018. Severe weather affecting freight leaving Minas Gerais has impacted your shipment originally promised for delivery by 29 August 2018.
>
> To resolve this, we have arranged free expedited shipping through an unaffected route. Your new delivery date is 31 August 2018.
>
> You do not need to do anything. The new route is already booked.
>
> Thank you for your patience,
> Customer Care Team

### DELAY: Update on your order b9eaa4a7

_Written by: Gemini. Order b9eaa4a76558ca828580d82dec38cca9._

> Hello,
>
> We sincerely apologize for the delay with your housewares order purchased on 5 August 2018 and originally promised for delivery by 17 August 2018. This delay was caused by severe weather affecting freight leaving Minas Gerais.
>
> Your new delivery date is 21 August 2018. To make things right, the freight charge of R$ 67.49 has been refunded to you.
>
> You do not need to do anything. The refund is automatic.
>
> Thank you for your patience,
> Customer Care Team

## One order traced end to end

Order `14a05c02d483800864e5c19a3a7f0ee2`

- **Item:** cool_stuff, 0.2 kg, 1 L, seller santa rita do sapucai/MG to customer sao paulo/SP
- **Retrieval:** filter {'seller_state': {'$in': ['MG']}}
- **Logistics:** baseline ETA 2018-08-29, promised 2018-08-29, new ETA 2018-09-02
- **Logistics:** Buffer 0 days, delay 4 days, so 4 days late: HIGH
- **Decision:** R3 REROUTE: Free expedited shipping through an unaffected route. Small goods move easily by another carrier: 2 extra days instead of 4
- **Email:** Update on your order 14a05c02

## Step trace

| step | count | ms | detail |
|---|---|---|---|
| 1. Parse disruption | 0 | 2974 | A weather disruption delays freight leaving the state of Minas Gerais (MG) by 4 days. (parsed by gemini) |
| 2. Retrieve affected items | 731 | 373 | filter {'seller_state': {'$in': ['MG']}}; 50 best matches for 'electronics and computer shipments' |
| 3. Analyse impact | 678 | 3 | 87 of 678 orders become late |
| 4. Decide actions | 678 | 0 | rules R0 to R4, first match wins |
| 5. Write customer emails | 2 | 3573 | written by gemini |
| 6. Write report | 0 | 2268 | Gemini calls 4, tokens 2980 |

**LLM notes:**

- gemini-3.6-flash was unavailable (gemini-3.6-flash: HTTP 429), so gemini-3.5-flash-lite answered
