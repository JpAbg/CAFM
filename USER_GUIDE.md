# CAFM User Guide

This guide explains how facility staff use CAFM day to day. It is for facility managers, coordinators, technicians, requesters, and vendors.

For installation, updates, and technical requirements, see [README.md](README.md).

## Start here

Open the **CAFM** workspace from the Desk. The **Facility Management Dashboard** shows maintenance requests, work orders, priorities, costs, overdue work, and preventive maintenance.

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

## Dashboard and reports

Use the **Facility Management Dashboard** for a quick operational view:

- Open requests and overdue work
- Work orders by priority and category
- Maintenance cost by site and building
- Asset downtime and recurring failures
- Preventive maintenance compliance and calendar
- Escalation number cards

Use reports for detailed analysis:

- Asset Maintenance History
- Maintenance Cost Report
- Maintenance Request Report
- Preventive Maintenance Report
- Technician Performance Report
- Work Order Report
- Preventive Maintenance Calendar

Set report filters first, then refresh the report before exporting or sharing results.

## Good operating habits

- Use clear request subjects: describe the asset, problem, and location.
- Always select the correct Facility Location and Asset.
- Set realistic planned start and end times.
- Update work-order status as work changes.
- Record material and labour accurately so costs and dashboards stay reliable.
- Close or resolve completed work promptly.
- Review overdue cards and preventive maintenance regularly.
- Print QR labels only after CAFM is available from the devices that will scan them.

## Getting help

If a record is missing, an action is unavailable, or an assignment does not appear:

1. Refresh the page once.
2. Check that the correct Company, Facility Location, and Asset are selected.
3. Check your role and permissions with the Facility Manager.
4. Include the record number and a screenshot when reporting a problem.
