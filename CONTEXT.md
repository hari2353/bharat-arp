# Bharat ARP Domain

Bharat ARP is a decision-support and workflow product for recovering overdue
B2B receivables. The connected ERP or accounting system remains the system of
record; Bharat ARP owns collection cases, recommendations, approvals, and
outcomes.

## Language

**Tenant**:
The legal business workspace whose financial data is isolated from every other
workspace. _Avoid_: account, customer, organization (unless referring to a
legal entity in source data).

**Customer Account**:
A buyer organization aggregated across its invoices, payments, contacts,
disputes, and collection history. _Avoid_: account (ambiguous with Tenant),
client, debtor.

**Invoice**:
A source-system billing record that creates an amount due from a Customer
Account. _Avoid_: bill, payment request.

**Outstanding Balance**:
The amount still due after valid payment allocations, credit notes, and other
source-system adjustments. _Avoid_: invoice amount, face value.

**Payment Allocation**:
An explicit relationship between a payment and one or more invoices. _Avoid_:
payment match (too vague), receipt.

**Collection Case**:
The operational work item for deciding and tracking how to recover one
Customer Account's overdue exposure. _Avoid_: ticket, task, alert.

**Promise to Pay**:
A customer- or staff-recorded commitment containing an expected payment date,
amount, source, and status. _Avoid_: forecast, commitment (too broad).

**Collection Proposal**:
An evidence-backed recommended next action that has not yet been approved.
_Avoid_: agent action, command, automation.

**Approval**:
An explicit authorization by an eligible user for a specific proposal and its
bounded side effect. _Avoid_: confidence, acceptance.

**Collection Outcome**:
The observed result of a proposal or case, such as payment received, promise
kept, promise broken, dispute opened, or no response. _Avoid_: success,
conversion.

**Source Record**:
An imported or connected record with source system, source identifier,
observed-at time, and raw-payload reference. _Avoid_: external data.

**Policy Version**:
The immutable ruleset used to produce a proposal. _Avoid_: prompt version,
model version (a model may be one input to a future policy).

**Communication Eligibility**:
The evaluated permission and operational readiness to contact a specific person
through a specific channel. A phone number alone is not eligibility. _Avoid_:
contactable, opted-in (unless consent is actually known).

**Payment**:
A source-system record of money received or posted against a Tenant. _Avoid_:
allocation, receipt (an allocation is a relationship, not the payment itself).

**Credit Note**:
A source adjustment that reduces the amount due on an Invoice. _Avoid_:
refund, discount.

**Dispute**:
An unresolved customer or internal challenge to an Invoice or delivery-related
obligation. _Avoid_: complaint, exception (a data-quality exception is
different).

**Contact**:
A person and channel record associated with a Customer Account, including
permission evidence. _Avoid_: phone number, recipient.

**Legal Entity**:
The registered business entity responsible for the source accounting records.
In the validation MVP, one deployment Tenant maps to one Legal Entity. _Avoid_:
company (ambiguous with source-system company).

**Import Batch**:
A versioned set of source files processed together with validation and
provenance metadata. _Avoid_: snapshot (a batch may contain deltas).

**Data-Quality Exception**:
A source or normalization condition that prevents a fact from being safely
used in decisioning. _Avoid_: warning, missing data.

**Risk Flag**:
An evidence-based condition that changes a proposal's permitted action or
requires human review. _Avoid_: model confidence, score.

**Policy Input**:
A defined, versioned fact available to a decision policy, including its
availability and freshness state. _Avoid_: feature (too implementation-specific).

**Source Snapshot**:
The set of source facts visible at a stated as-of date. A snapshot never
silently deletes prior facts. _Avoid_: import batch.

**Assignment**:
The explicit association of a Collection Case with an authorized operator.
_Avoid_: ownership (ambiguous with data ownership).
