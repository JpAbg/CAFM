function init_override() {
    if (!window.frappe?.widget?.widget_factory?.chart) {
        setTimeout(init_override, 200);
        return;
    }

    if (window.__cafm_horizontal_bar_chart_installed) {
        return;
    }
    window.__cafm_horizontal_bar_chart_installed = true;

    const ChartWidget = frappe.widget.widget_factory.chart;

    const priority_colors = Object.freeze({
        critical: "#DC2626",
        high: "#F59E0B",
        medium: "#3B82F6",
        low: "#22C55E",
    });

    const original_get_chart_args = ChartWidget.prototype.get_chart_args;
    const original_render = ChartWidget.prototype.render;

    ChartWidget.prototype.get_chart_args = function () {
        const args = original_get_chart_args.call(this);

        if (this.chart_doc?.type === "Bar") {
            args.horizontal_bars =
                Boolean(this.chart_doc.horizontal_bars) ||
                Boolean(this.chart_doc.custom_horizontal_bars);
        }

        const chart_name = String(this.chart_doc?.name || "")
            .trim()
            .toLowerCase();
        if (chart_name === "work orders by priority") {
            const labels = args.data?.labels || [];
            const priority_order = ["critical", "high", "medium", "low"];
            const ordered_items = labels
                .map((label, index) => ({
                    label,
                    index,
                    priority: String(label).trim().toLowerCase(),
                }))
                .sort((left, right) => {
                    const left_index = priority_order.indexOf(left.priority);
                    const right_index = priority_order.indexOf(right.priority);
                    return (
                        (left_index === -1 ? priority_order.length : left_index) -
                        (right_index === -1 ? priority_order.length : right_index)
                    );
                });

            args.data.labels = ordered_items.map((item) => item.label);
            args.data.datasets = (args.data.datasets || []).map((dataset) => ({
                ...dataset,
                values: ordered_items.map((item) => dataset.values?.[item.index]),
            }));
            args.colors = ordered_items.map((item) => {
                return (
                    priority_colors[item.priority] ||
                    args.colors?.[item.index] ||
                    "#64748B"
                );
            });
        }

        return args;
    };

    ChartWidget.prototype.render = async function (...call_args) {
        if (this.chart_doc?.name) {
            const fresh_chart_doc = await frappe.db.get_doc(
                "Dashboard Chart",
                this.chart_doc.name
            );
            if (fresh_chart_doc) {
                this.chart_doc = fresh_chart_doc;
            }
        }

        const is_horizontal =
            this.chart_doc?.type === "Bar" &&
            (this.chart_doc?.horizontal_bars || this.chart_doc?.custom_horizontal_bars) &&
            this.data?.labels?.length;

        if (!is_horizontal) {
            const uses_flexible_legend = ["Donut", "Percentage"].includes(
                this.chart_doc?.type
            ) || String(this.chart_doc?.name || "").trim().toLowerCase() ===
                "maintenance cost by site and building";

            if (uses_flexible_legend) {
                observe_chart_legend(this);
            }

            return original_render.apply(this, call_args);
        }

        // Render horizontal charts directly. Calling the standard renderer first
        // creates a race where its asynchronous vertical chart may overwrite ours.
        this.loading.hide();
        this.empty.hide();
        this.chart_wrapper.show();
        this.$summary?.hide();

        this.chart_doc.document_type = await this.get_source_doctype();
        if (this.chart_doc.document_type) {
            await new Promise(resolve =>
                frappe.model.with_doctype(this.chart_doc.document_type, resolve)
            );
        }

        const chart_args = this.get_chart_args();
        if (!chart_args?.data?.datasets?.length) {
            return;
        }

        delete this.dashboard_chart;

        const all_values = chart_args.data.datasets
            .flatMap(ds => (ds.values || []).map(Number))
            .filter(v => !isNaN(v));

        const min_value = Math.min(0, ...all_values);
        const max_value = Math.max(0, ...all_values);
        const { ticks } = get_nice_ticks(min_value, max_value);

        render_horizontal_bar_chart(
            this.chart_wrapper[0],
            chart_args,
            ticks,
            this.chart_doc?.color
        );

        if (this.width === "Full" && this.summary) {
            this.set_summary();
        }
    };

    function get_nice_ticks(min_value, max_value, tick_count = 5) {
        const range = nice_num(max_value - min_value, false);
        const tick_spacing = nice_num(range / (tick_count - 1), true);

        const nice_min = Math.floor(min_value / tick_spacing) * tick_spacing;
        const nice_max = Math.ceil(max_value / tick_spacing) * tick_spacing;

        const ticks = [];
        for (let v = nice_min; v <= nice_max + tick_spacing * 0.5; v += tick_spacing) {
            ticks.push(Math.round(v * 1000) / 1000); // avoid float drift
        }

        return { ticks, nice_min, nice_max };
    }

    function nice_num(range, round) {
        if (range === 0) range = 1;

        const exponent = Math.floor(Math.log10(range));
        const fraction = range / Math.pow(10, exponent);
        let nice_fraction;

        if (round) {
            if (fraction < 1.5) nice_fraction = 1;
            else if (fraction < 3) nice_fraction = 2;
            else if (fraction < 7) nice_fraction = 5;
            else nice_fraction = 10;
        } else {
            if (fraction <= 1) nice_fraction = 1;
            else if (fraction <= 2) nice_fraction = 2;
            else if (fraction <= 5) nice_fraction = 5;
            else nice_fraction = 10;
        }

        return nice_fraction * Math.pow(10, exponent);
    }

    function render_horizontal_bar_chart(
        container,
        options,
        nice_ticks,
        chart_color
    ) {

        const $container = $(container);
        $container.empty();

        const { labels = [], datasets = [] } = options.data || {};

        const valid_option_colors = (options.colors || []).filter(
            color => typeof color === "string" && color.trim()
        );
        const selected_color =
            typeof chart_color === "string" ? chart_color.trim() : "";
        const bar_colors = selected_color
            ? [selected_color]
            : valid_option_colors.length
                ? valid_option_colors
                : ["#2490ef"];

        if (!labels.length || !datasets.length || !nice_ticks?.length) return;

        const width = Math.max($container.width() || 500, 300);
        const margin = { top: 15, right: 30, bottom: 40, left: 78 };
        const minimum_row_height = 38;
        const content_height = labels.length * minimum_row_height;
        const height = Math.max(
            Number(options.height) || 240,
            margin.top + margin.bottom + content_height
        );
        const chart_width = width - margin.left - margin.right;
        const chart_height = height - margin.top - margin.bottom;
        const row_height = chart_height / labels.length;

        const nice_min = nice_ticks[0];
        const nice_max = nice_ticks[nice_ticks.length - 1];
        const value_range = nice_max - nice_min || 1;
        const value_to_x = (v) => margin.left + ((v - nice_min) / value_range) * chart_width;
        const zero_x = value_to_x(0);

        const svg = svg_element("svg");
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", height);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.style.display = "block";

        const add_line = (x1, y1, x2, y2, opacity) => {
            const line = svg_element("line");
            Object.entries({ x1, y1, x2, y2, stroke: "currentColor", opacity }).forEach(
                ([k, v]) => line.setAttribute(k, v)
            );
            svg.appendChild(line);
        };

        const add_text = (
            text,
            x,
            y,
            anchor,
            opacity = 1,
            size = 12,
            tooltip_text = null
        ) => {
            const t = svg_element("text");
            t.textContent = text;
            Object.entries({
                x, y, "text-anchor": anchor, "font-size": size,
                fill: "currentColor", opacity,
            }).forEach(([k, v]) => t.setAttribute(k, v));
            if (tooltip_text) {
                const tooltip = svg_element("title");
                tooltip.textContent = tooltip_text;
                t.appendChild(tooltip);
            }
            svg.appendChild(t);
            return t;
        };

        // Gridlines + axis ticks
        nice_ticks.forEach((value) => {
            const x = value_to_x(value);
            add_line(x, margin.top, x, margin.top + chart_height, 0.08);
            add_text(format_number(value), x, margin.top + chart_height + 22, "middle", 0.65, 11);
        });

        // Zero line
        add_line(zero_x, margin.top, zero_x, margin.top + chart_height, 0.25);

        // Rows: category label + bars per dataset
        const dataset_count = datasets.length;
        const bar_height = Math.min(22, (row_height * 0.7) / dataset_count);

        labels.forEach((label, index) => {
            const group_y = margin.top + index * row_height;
            const group_center = group_y + row_height / 2;

            const full_label = String(label);
            const display_label = options.horizontal_bars
                ? compact_horizontal_label(full_label)
                : full_label;
            add_text(
                display_label,
                margin.left - 12,
                group_center + 4,
                "end",
                1,
                12,
                display_label === full_label ? null : full_label
            );

            datasets.forEach((dataset, dataset_index) => {
                const value = Number(dataset.values?.[index]) || 0;
                const value_x = value_to_x(value);
                const bar_x = Math.min(zero_x, value_x);
                const bar_width = Math.abs(value_x - zero_x);
                const bar_y =
                    group_center - (dataset_count * bar_height) / 2 +
                    dataset_index * bar_height;

                const bar = svg_element("rect");

                Object.entries({
                    x: bar_x,
                    y: bar_y,
                    width: Math.max(bar_width, 1),
                    height: Math.max(bar_height - 2, 1),
                    rx: 2,
                    fill: bar_colors[dataset_index % bar_colors.length],
                }).forEach(([k, v]) => bar.setAttribute(k, v));

                const tooltip = svg_element("title");
                tooltip.textContent = dataset.name
                    ? `${dataset.name}: ${format_number(value)}`
                    : format_number(value);

                bar.appendChild(tooltip);
                svg.appendChild(bar);
            });
        });

        // X axis baseline
        add_line(margin.left, margin.top + chart_height, margin.left + chart_width, margin.top + chart_height, 0.2);

        $container.append(svg);
    }

    function svg_element(name) {
        return document.createElementNS("http://www.w3.org/2000/svg", name);
    }

    function format_number(value) {
        if (frappe.utils && frappe.utils.format_chart_axis_number) {
            return frappe.utils.format_chart_axis_number(value);
        }
        return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
    }

    function truncate_label(label, max_characters) {
        if (label.length <= max_characters) return label;
        return `${label.slice(0, max_characters - 1).trimEnd()}…`;
    }
    function compact_horizontal_label(label) {
        const asset_id = label.match(/^ACC-ASS-\d{4}-(\d+)$/i);
        if (asset_id) {
            return `ACC-${asset_id[1].slice(-2)}`;
        }

        const words = label.trim().split(/\s+/);
        if (words.length > 1) return words[0];
        if (label.length <= 12) return label;

        return `${label.slice(0, 4)}...${label.slice(-5)}`;
    }

    function observe_chart_legend(widget) {
        const container = widget.chart_wrapper?.[0];
        if (!container) return;

        widget.__cafm_legend_observer?.disconnect();

        let frame;
        const apply_spacing = () => {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() =>
                fix_chart_legend_spacing(widget)
            );
        };
        const observer = new MutationObserver(apply_spacing);

        observer.observe(container, {
            childList: true,
            subtree: true,
        });
        widget.__cafm_legend_observer = observer;
        apply_spacing();

        setTimeout(() => {
            apply_spacing();
            observer.disconnect();
            if (widget.__cafm_legend_observer === observer) {
                delete widget.__cafm_legend_observer;
            }
        }, 3000);
    }

    function fix_chart_legend_spacing(widget) {
        const container = widget.chart_wrapper?.[0];
        const svg = container?.querySelector("svg.frappe-chart");
        const legend = svg?.querySelector(".chart-legend");
        const legend_items = legend
            ? Array.from(legend.children).filter(
                item => item.tagName?.toLowerCase() === "g"
            )
            : [];

        if (!svg || !legend_items.length) return;

        const uses_category_legend = ["Donut", "Percentage"].includes(
            widget.chart_doc?.type
        );
        const labels = uses_category_legend
            ? widget.data?.labels || []
            : (widget.data?.datasets || []).map((dataset) => dataset.name);
        const view_box = svg.viewBox?.baseVal;
        const available_width = Math.max(
            (view_box?.width || svg.clientWidth || 300) - 100,
            200
        );
        const row_height = 60;

        const item_widths = legend_items.map((item, index) => {
            const label = item.querySelector(".legend-dataset-label");
            const value = item.querySelector(".legend-dataset-value");

            if (
                label &&
                labels[index] !== undefined &&
                label.textContent !== String(labels[index])
            ) {
                label.textContent = String(labels[index]);
            }

            const label_width = label?.getComputedTextLength?.() || 0;
            const value_width = value?.getComputedTextLength?.() || 0;
            return Math.max(label_width, value_width) + 28;
        });

        const minimum_gap = 24;
        const content_width = item_widths.reduce(
            (total, width) => total + width,
            0
        );
        const fits_one_row =
            content_width +
                minimum_gap * Math.max(legend_items.length - 1, 0) <=
            available_width;
        let x = 0;
        let y = 0;

        if (fits_one_row) {
            const gap = legend_items.length > 1
                ? (available_width - content_width) /
                    (legend_items.length - 1)
                : 0;

            legend_items.forEach((item, index) => {
                item.setAttribute("transform", `translate(${x}, 0)`);
                x += item_widths[index] + gap;
            });
        } else {
            legend_items.forEach((item, index) => {
                if (x > 0 && x + item_widths[index] > available_width) {
                    x = 0;
                    y += row_height;
                }

                item.setAttribute("transform", `translate(${x}, ${y})`);
                x += item_widths[index] + minimum_gap;
            });
        }

        if (!svg.dataset.cafmBaseHeight) {
            svg.dataset.cafmBaseHeight = String(
                view_box?.height || Number(svg.getAttribute("height")) || 0
            );
        }

        const base_height = Number(svg.dataset.cafmBaseHeight);
        if (base_height) {
            const adjusted_height = base_height + y;
            const view_box_width = view_box?.width || svg.clientWidth;
            svg.setAttribute(
                "viewBox",
                `0 0 ${view_box_width} ${adjusted_height}`
            );
            svg.setAttribute("height", adjusted_height);
        }
    }

}

init_override();

function init_custom_number_card_trends() {
    const NumberCardWidget = window.frappe?.widget?.widget_factory?.number_card;
    if (!NumberCardWidget) {
        setTimeout(init_custom_number_card_trends, 10);
        return;
    }

    if (window.__cafm_custom_number_card_trends_installed) return;
    window.__cafm_custom_number_card_trends_installed = true;

    const original_render_stats = NumberCardWidget.prototype.render_stats;
    NumberCardWidget.prototype.render_stats = function () {
        const trend = Number(this.data?.trend_percentage);
        if (
            this.card_doc?.type !== "Custom" ||
            this.data?.trend_percentage === null ||
            this.data?.trend_percentage === undefined ||
            Number.isNaN(trend)
        ) {
            return original_render_stats.call(this);
        }

        let caret_html = "";
        let color_class = "grey-stat";
        if (trend > 0) {
            caret_html = `<span class="indicator-pill-round green">
                ${frappe.utils.icon("es-line-arrow-up-right", "xs")}
            </span>`;
            color_class = "red-stat";
        } else if (trend < 0) {
            caret_html = `<span class="indicator-pill-round red">
                ${frappe.utils.icon("arrow-down-right", "xs")}
            </span>`;
            color_class = "red-stat";
        }

        const percentage = new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 2,
        }).format(Math.abs(trend));
        const label = __(this.data.trend_label || "since yesterday");
        $(this.body).find(".widget-content").append(`
            <div class="card-stats ${color_class}">
                <span class="percentage-stat-area">
                    ${caret_html} ${percentage} % ${label}
                </span>
            </div>
        `);
    };
}

init_custom_number_card_trends();
