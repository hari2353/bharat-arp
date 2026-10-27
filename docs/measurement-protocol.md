# Pilot Measurement Protocol

The pilot measures whether account-level prioritization and Promise-to-Pay
tracking outperform the customer's current collections process. It does not
claim causal impact from a payment that merely happened after a message.

## Before Pilot Start

Record for each pilot:

- current ERPNext dunning/reminder workflow and any manual spreadsheet process
- 8-12 weeks of historical 30+, 60+, and 90+ day ageing
- in-scope Customer Accounts and opening Outstanding Balance
- review hours per week and time to first appropriate action
- baseline Promise-to-Pay capture, broken-promise rate, and data-quality rate
- manual data-cleaning hours required to produce the CSV contract

## Cohorts and Windows

- `baseline`: the 8-12 weeks before the pilot, excluding known one-off events
- `pilot_priority`: accounts surfaced in the top priority cohort
- `pilot_non_priority`: eligible accounts not surfaced in the top cohort
- observation window: 60-90 days, with weekly snapshots
- payments already pending or promised before the pilot are marked `in_flight`
  and reported separately

## Measures

- recovered cash by cohort, gross and net of credit notes
- change in 30+, 60+, and 90+ day exposure
- time from due date to first appropriate documented action
- finance review hours per week
- Promise-to-Pay acceptance, fulfilment, partial fulfilment, and broken rate
- percentage of exposure and accounts decision-eligible
- data-quality exceptions by type and age

## Language Rules

Reports may say:

- “payment observed after proposal”
- “Promise to Pay fulfilled”
- “ageing changed during the pilot”

Reports may not say “the proposal caused payment” unless a separately approved
experimental design defines treatment assignment, control, contamination,
observation window, and analysis before the experiment begins.

## Exit Criteria

A pilot is commercially promising only when it meets all of these:

- at least 80% of priority exposure is decision-eligible, not merely classified
  as an exception;
- at least 80% of priority cases receive a documented action within one business
  day;
- finance review time falls by at least 25% versus baseline, or the customer
  documents an equivalent operational benefit;
- overdue exposure in the priority cohort improves versus the agreed baseline
  without increased dispute or opt-out rates;
- the customer agrees to renew or pay for the next period.

Failure of the wedge is declared if pilots only request ordinary reminders,
invoice sending, GST features, or data cleanup without paying for decisioning.
