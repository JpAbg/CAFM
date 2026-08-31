frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Preventive Maintenance Heatmap"] = {
    method: "cafm.cafm.dashboard_chart_source.preventive_maintenance_heatmap.preventive_maintenance_heatmap.get",
};

if (!frappe.cafm_preventive_heatmap_bound) {
    frappe.cafm_preventive_heatmap_bound = true;

    const day_colors = {
        1: "#c7edcc",
        2: "#91d99b",
        3: "#65c875",
        4: "#24a148",
        5: "#0d6b2d",
    };

    const open_report_for_day = (square) => {
        const date = square.getAttribute("data-date");
        const count = Number(square.getAttribute("data-value") || 0);

        if (!date || count <= 0) {
            return;
        }

        frappe.set_route("query-report", "Preventive Maintenance Calendar", {
            from_date: date,
            to_date: date,
            company: frappe.defaults.get_user_default("Company"),
            work_order_status: "All",
        });
    };

    const bind_heatmap = () => {
        const widget = document.querySelector(
            '[data-widget-name="Preventive Maintenance Calendar"]'
        );
        const root = widget && widget.shadowRoot;

        if (!root || root.cafmHeatmapBound) {
            return Boolean(root);
        }

        root.cafmHeatmapBound = true;
        const apply_day_colours = () => {
            root.querySelectorAll(".day[data-value]").forEach((square) => {
                const count = Math.min(
                    5,
                    Math.max(0, Number(square.getAttribute("data-value") || 0))
                );

                if (count > 0) {
                    square.setAttribute("fill", day_colors[count]);
                    square.style.fill = day_colors[count];
                    square.style.cursor = "pointer";
                }
            });
        };

        root.addEventListener("click", (event) => {
            const square = event.target.closest && event.target.closest(".day[data-value]");
            if (square) {
                open_report_for_day(square);
            }
        });

        new MutationObserver(apply_day_colours).observe(root, {
            childList: true,
            subtree: true,
        });
        apply_day_colours();
        return true;
    };

    const open_day_from_event = (event) => {
        const path = event.composedPath ? event.composedPath() : [];
        const square = path.find(
            (element) =>
                element &&
                element.classList &&
                element.classList.contains("day") &&
                element.hasAttribute &&
                element.hasAttribute("data-date")
        );

        if (square) {
            open_report_for_day(square);
        }
    };

    // Click events from dashboard charts cross their component boundary.
    // Capturing them here also covers charts rebuilt after a dashboard refresh.
    document.addEventListener("click", open_day_from_event, true);

    const wait_for_heatmap = (attempts = 0) => {
        if (!bind_heatmap() && attempts < 20) {
            setTimeout(() => wait_for_heatmap(attempts + 1), 250);
        }
    };

    wait_for_heatmap();
}
