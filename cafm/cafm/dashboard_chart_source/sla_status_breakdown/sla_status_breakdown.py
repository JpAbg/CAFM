import frappe


SLA_STATUSES = (
    "On Track",
    "Response Breached",
    "Resolution Breached",
    "Met",
)


@frappe.whitelist()
def get(**kwargs):
    counts = frappe.get_all(
        "Facility Work Order",
        filters={"sla_policy": ["is", "set"]},
        fields=["sla_status", "count(name) as total"],
        group_by="sla_status",
    )
    count_by_status = {row.sla_status: row.total for row in counts}
    return {
        "labels": list(SLA_STATUSES),
        "datasets": [
            {
                "name": "Work Orders by SLA Status",
                "values": [count_by_status.get(status, 0) for status in SLA_STATUSES],
            }
        ],
    }
