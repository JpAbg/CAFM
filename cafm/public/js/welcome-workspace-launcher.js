(function () {
  const manager_roles = ["Administrator", "System Manager", "Facility Manager", "Facility Coordinator"];

  function add_launcher() {
    const page_path = decodeURIComponent(window.location.pathname).toLowerCase();
    const is_welcome_workspace = page_path.endsWith("/app/workspaces/welcome workspace")
      || page_path.endsWith("/app/welcome-workspace");
    if (!is_welcome_workspace) return;

    $(".layout-main-section *").filter(function () {
      const text = $(this).text().trim();
      return text === "Hi," || text.indexOf("I guess you don't have access to any workspace yet") === 0;
    }).remove();

    const roles = frappe.user_roles || [];
    if (manager_roles.some(function (role) { return roles.includes(role); })) return;

    let label = null;
    let description = null;
    let action = null;

    if (roles.includes("Technician")) {
      label = "Open Technician Mobile";
      description = "View and update the maintenance work assigned to you.";
      action = function () { frappe.set_route("technician-mobile"); };
    } else if (roles.includes("Employee")) {
      label = "Open Facility Portal";
      description = "Submit and track your own facility requests.";
      action = function () { window.location.assign("/facility-portal"); };
    }

    if (!label || document.getElementById("cafm-welcome-launcher")) return;

    const target = $(".layout-main-section").first().length
      ? $(".layout-main-section").first()
      : $(".page-body").first();
    if (!target.length) return;

    const card = $('<section id="cafm-welcome-launcher" class="cafm-welcome-launcher"><span>CAFM</span><h2></h2><p></p><button class="btn btn-primary"></button></section>');
    card.find("h2").text(label);
    card.find("p").text(description);
    card.find("button").text(label).on("click", action);
    target.prepend(card);
  }

  function schedule_launcher() {
    let attempts = 0;
    const timer = setInterval(function () {
      add_launcher();
      attempts += 1;
      if (attempts >= 20) {
        clearInterval(timer);
      }
    }, 150);
  }

  $(function () {
    schedule_launcher();
    setTimeout(schedule_launcher, 600);
  });
  frappe.dom.set_style(".cafm-welcome-launcher{max-width:620px;margin:24px auto;padding:28px;border:1px solid #d7e6f1;border-radius:16px;background:linear-gradient(135deg,#f5fbff,#ffffff);text-align:center;box-shadow:0 7px 20px rgba(24,76,112,.07)}.cafm-welcome-launcher span{display:inline-block;padding:4px 9px;border-radius:99px;background:#e4f3fd;color:#1c679d;font-size:11px;font-weight:800;letter-spacing:.5px}.cafm-welcome-launcher h2{margin:13px 0 7px;color:#174f80;font-size:25px}.cafm-welcome-launcher p{margin:0 auto 19px;max-width:400px;color:#587187}.cafm-welcome-launcher .btn{padding:10px 17px;background:#0f5a97;border-color:#0f5a97}");
})();
