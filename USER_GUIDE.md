# CAFM User Guide

This guide explains how facility staff use CAFM day to day. It is for facility managers, coordinators, technicians, requesters, and vendors.

For installation, updates, and technical requirements, see [README.md](README.md).

## Start here

Open **Facilities** from the Desk sidebar. This CAFM workspace provides shortcuts to locations, assets, requests, work orders, preventive maintenance, utilities, and reports. The **Facility Management Dashboard** shows maintenance requests, work orders, priorities, costs, overdue work, and preventive maintenance.

Use the search bar to find an Asset, Facility Location, Maintenance Request, or Facility Work Order by name.

## Roles

| Role | Main responsibility |
| --- | --- |
| Facility Manager | Oversees maintenance, teams, suppliers, costs, and escalations. |
| Facility Coordinator | Receives requests, plans work, assigns technicians, and follows up. |
| Technician | Views assigned work and records progress, time, materials, and resolutions. |
| Requester / Employee | Raises maintenance requests and follows their own requests. |
| Vendor | Works with assigned external service work and provider information. |

If an action is not available, ask the Facility Manager to check your role and permissions.

## Employee login accounts

When an active Employee is saved with a Company Email, CAFM automatically creates and links a login account. If no Company Email is available, it uses Personal Email instead.

The employee receives Frappe's standard invitation email and chooses their own password. CAFM never assigns a shared default password.

New employee accounts receive the **Employee** and **Requester / Employee** roles after the Employee record is saved. An employee marked as a Facility Technician also receives the **Technician** role. CAFM creates a unique username from the employee name when needed. If email is not configured on the site, a Facility Manager can use the standard password-reset action on the User record after email delivery is configured.

## Facility locations

Create the facility structure before registering assets:

1. Create a **Facility Location** for the site.
2. Add its building, floor, and room details.
3. Select this Facility Location on Assets, Maintenance Requests, Work Orders, preventive plans, and inspections.

CAFM uses **Facility Location** as the business location. The standard ERPNext location is filled in automatically in the background.

## Assets

An Asset represents physical equipment such as an HVAC unit, pump, generator, electrical panel, or fire-safety device.

To create an Asset:

1. Open **Asset** and select **Add Asset**.
2. Enter the Asset Name, Company, Asset Category, purchase information, and purchase value.
3. Set **Facility Location**, Criticality, and Operational Status.
4. Save the Asset.

The Asset page shows warranty details, open maintenance work, and completed maintenance history.

### Asset QR codes

Every Asset has an **Asset QR Code** section. Open **QR Code - Show QR Code** to preview it, then choose **Download QR Code** in the pop-up to save the label for printing.

Place the printed QR label on the real equipment. A signed-in technician scans it to open the correct Asset record without searching manually. From the record, choose **Maintenance - Create Maintenance Request**.

QR codes respect normal Asset permissions. They do not grant access to users who cannot use CAFM.

> **Note:** A phone must be able to reach the CAFM site address. QR codes created on a localhost development site work only on that computer. Use an office-network or hosted URL before rolling out printed labels.

## Employee facility portal

Employees can submit and follow their own facility requests through the **Facility Portal** at /facility-portal.

1. Open the portal while signed in with an Employee account.
2. Select **Submit Request**.
3. Enter the subject, facility location, request category, priority, and description.
4. Submit the request.

The **My Requests** list shows only requests submitted by that employee. A new request can be opened to review it, edited while it has not been converted into a work order, or withdrawn if it is no longer needed.

Once a coordinator plans the request, its related work order and status remain visible to the employee. Resolved and closed requests remain in the portal history for 30 days. Rejected requests are hidden from the list.

## Maintenance requests

A Maintenance Request starts as an **Issue** in Frappe.

1. Open **Issue** and select **Add Issue**.
2. Enter a clear subject and description.
3. Select the Company and Facility Location.
4. Select the affected Asset when applicable.
5. Select the request category and priority.
6. Save and submit the request using the available workflow action.

The selected Asset can automatically raise the priority when its CAFM Criticality or category requires it.

A coordinator opens the request and selects **Create - Create Work Order** when work needs to be planned.

## Work orders

A **Facility Work Order** is the planned and tracked job created from a request.

The coordinator should:

1. Set the Asset and Facility Location.
2. Enter the subject, priority, planned start, and planned end.
3. Assign the appropriate technician.
4. Start the workflow and monitor progress.

The technician should:

1. Open assigned work orders.
2. Move work through Draft, Assigned, In Progress, or Pending as appropriate.
3. Record labour hours, downtime, materials used, findings, and the resolution.
4. Complete the work when the job is finished.

The dashboard and reports use this information for workload, response, cost, downtime, and overdue measurements.

## Technician Mobile

Technicians can use **Technician Mobile** at /app/technician-mobile for a focused view of their workload.

- The page lists only work orders assigned to the signed-in technician.
- Use the left panel to switch between all active work, Assigned, In Progress, Pending, Overdue, and Completed history.
- Completed work stays available for the last 30 days.
- Use the Task range, Priority, and Location filters to narrow the list.
- Select a work-order card, or a notification item, to open the corresponding work order.
- The bell shows assigned-work notifications. Opening the panel marks new notifications as read. Use **x** to dismiss an individual item or **Clear all** to clear the displayed list.

Update the work order itself to record progress and completion. Technician Mobile is a faster entry point; it does not replace the work-order record.

## Escalated and overdue work

CAFM automatically escalates overdue work orders at these thresholds:

- **Critical work order escalation**: 1 hour overdue.
- **Coordinator overdue escalation**: 4 hours overdue.
- **Manager overdue escalation**: 24 hours overdue.

The Facility Management Dashboard includes number cards for each level. A work order moves out of the earlier count when it reaches the next level, so each card represents its own overdue range.

Keep planned end dates accurate. This is what makes escalation reporting useful.

## Preventive maintenance

Use a **Preventive Maintenance Plan** to schedule recurring work for an Asset.

1. Create a plan.
2. Select the Company, Facility Location, Asset, maintenance task, frequency, and planned schedule.
3. Activate the plan.
4. CAFM creates the related preventive work orders according to the schedule.
5. Complete each generated work order normally.

Use the **Preventive Maintenance Calendar** report and dashboard heatmap to review upcoming and active preventive work. Filter by date range, company, location, asset, technician, and work-order status.

Cancelled, closed, and resolved work does not count as active preventive work on the calendar.

## Inspections

Use **Facility Inspection Templates** to define reusable checklists. A template can be specific to a category or marked **General** for broad use.

1. Open **Facility Inspection** and create a new record.
2. Choose Manual or a scheduled source.
3. Select the Facility Location, Asset, and applicable Inspection Template.
4. Select the Inspector and planned date.
5. Complete the checklist and record findings.
6. Follow the workflow to complete, approve, reopen, reject, or cancel it as appropriate.

Inspection templates are filtered to match the selected asset/category. General templates remain available for broad inspections.

## Maintenance teams and technicians

Create **Asset Maintenance Teams** for groups such as HVAC, Electrical, Plumbing, or Emergency Response.

Add team members and select their maintenance role. A technician can belong to more than one team, such as HVAC and Emergency Response, so assign them based on their skills and availability.

Employee records can hold the technician flag, specialization, availability, maximum active work orders, and service categories.

## Warranty tracking

Complete the **Warranty** section on each Asset:

- Warranty Provider
- Warranty Start Date
- Warranty Expiry Date
- Warranty Reference
- Warranty Coverage
- Warranty Document

CAFM calculates the status automatically:

| Status | Meaning |
| --- | --- |
| Not Covered | No valid warranty expiry date is recorded. |
| Pending | Warranty has not started yet. |
| Active | The Asset is currently covered. |
| Expiring Soon | Warranty is nearing its expiry date. |
| Expired | Warranty coverage has ended. |

Mark a work order as a warranty claim only when the Asset is within its valid warranty period.

## SLA tracking

Each Work Order automatically receives the best matching active **Facility SLA Policy** based on its priority and, when configured, its company or category. The Work Order shows the response due time, resolution due time, achieved times, and current SLA status.

Response is recorded when the Work Order is assigned. Resolution is recorded when it is resolved or closed. CAFM measures the default policies using 24/7 elapsed hours and does not pause the timer while a Work Order is Pending. Facility Managers and Coordinators receive an alert when a response or resolution target is breached.

## Vendor quotations and service contracts

Use **Facility Service Provider** for approved external vendors. Each provider is linked to its ERPNext Supplier, contact details, service categories, availability, and vendor user.

From a saved Facility Work Order, use **Vendor - Request Vendor Quotation** to create a quotation record. Add one quotation for each vendor, including the scope, expected completion time, valid-until date, warranty, price, tax, and attached quotation document.

When a quotation has been received, open it and select **Actions - Select Quotation**. CAFM marks that quotation as selected, rejects the other open quotations for the same job, assigns the external vendor to the Work Order, and records the agreed cost.

Use **Facility Service Contract** for longer agreements. Set the provider, dates, value, document, and coverage scope. A contract may cover all assets, one facility location, one asset, or one service category. The Work Order's **Vendor - View Matching Contracts** action identifies active contracts that apply to that job.

## Utility monitoring

Use utility monitoring to record meter usage, cost, demand, and environmental indicators.

1. Create a **Utility Meter** for each electricity, water, natural-gas, fuel, or other meter.
2. Set its company, site or building, supplier, unit, and cost per unit.
3. Create the first **Utility Reading** and mark it as **Opening Reading**. This establishes the baseline and has no calculated consumption.
4. Add later readings for the same meter. CAFM uses the previous reading to calculate consumption and estimated cost.
5. Review the **Utility Consumption Report** and **Utility Consumption Dashboard**.

The dashboard includes usage and cost trends, peak-demand indicators, carbon estimates, forecasts, anomalies, weather-normalized comparisons, and allocation views when relevant records exist. Use these as management indicators and investigate unusual readings before acting on them.

For reliable results, record readings at consistent intervals and do not change the meter unit after readings have been entered.

## Dashboard and reports

Use the dashboards for a quick operational view:

- **Facility Management Dashboard:** requests, work orders, priorities, costs, overdue work, preventive maintenance, and escalations.
- **SLA Performance Dashboard:** response and resolution performance, breached work, and SLA trends.
- **Utility Consumption Dashboard:** meter reporting, consumption, cost, demand, forecast, carbon, and anomaly indicators.

Use reports for detailed analysis:

- Asset Maintenance History
- Maintenance Cost Report
- Maintenance Request Report
- Preventive Maintenance Report
- Technician Performance Report
- Work Order Report
- Preventive Maintenance Calendar
- Utility Consumption Report

Set report filters first, then refresh the report before exporting or sharing results.

## Good operating habits

- Use clear request subjects: describe the asset, problem, and location.
- Always select the correct Facility Location and Asset.
- Set realistic planned start and end times.
- Update work-order status as work changes.
- Record material and labour accurately so costs and dashboards stay reliable.
- Record utility readings consistently and mark only the first reading as Opening Reading.
- Close or resolve completed work promptly.
- Review overdue cards and preventive maintenance regularly.
- Print QR labels only after CAFM is available from the devices that will scan them.

## Getting help

If a record is missing, an action is unavailable, or an assignment does not appear:

1. Refresh the page once.
2. Check that the correct Company, Facility Location, and Asset are selected.
3. Check your role and permissions with the Facility Manager.
4. Include the record number and a screenshot when reporting a problem.
