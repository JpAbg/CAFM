# Copyright (c) 2026, Jean Paul Abou Gharib and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, getdate, nowdate


@frappe.whitelist()
def get(
    chart_name=None,
    chart=None,
    no_cache=None,
    filters=None,
    from_date=None,
    to_date=None,
    timespan=None,
    time_interval=None,
    heatmap_year=None,
):
    """Return daily counts of active preventive work orders for a heatmap."""
    year = cint(heatmap_year) or getdate(nowdate()).year
    start_date = f"{year}-01-01"
    end_date = f"{year + 1}-01-01"

    rows = frappe.db.sql(
        """
        SELECT
            UNIX_TIMESTAMP(scheduled_occurrence_date) AS timestamp,
            COUNT(*) AS work_order_count
        FROM `tabFacility Work Order`
        WHERE
            docstatus < 2
            AND work_order_type = 'Preventive'
            AND work_order_status NOT IN ('Resolved', 'Closed', 'Cancelled')
            AND scheduled_occurrence_date >= %(start_date)s
            AND scheduled_occurrence_date < %(end_date)s
        GROUP BY scheduled_occurrence_date
        ORDER BY scheduled_occurrence_date
        """,
        {"start_date": start_date, "end_date": end_date},
        as_list=True,
    )

    data_points = {int(timestamp): min(int(count), 5) for timestamp, count in rows if timestamp}
    # Keeps five tasks in the strongest visible heatmap band.
    # This date is outside the displayed year, so it is never shown to users.
    data_points[946684800] = 6

    return {
        "labels": [],
        "dataPoints": data_points,
        "start": start_date,
        "end": f"{year}-12-31",
    }
