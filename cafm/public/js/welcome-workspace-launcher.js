(function () {
  const manager_roles = ["Administrator", "System Manager", "Facility Manager", "Facility Coordinator"];

  function add_launcher() {
    const page_path = decodeURIComponent(window.location.pathname).toLowerCase();
    const is_welcome_workspace = page_path.endsWith("/app/workspaces/welcome workspace")
      || page_path.endsWith("/app/welcome-workspace");
    if (!is_welcome_workspace) return;

    remove_hi_message();

    const roles = frappe.user_roles || [];
    const is_manager = manager_roles.some(function (role) { return roles.includes(role); });
    if (is_manager) return;

    let launchers = [];

    if (roles.includes("Technician")) {
      launchers = [
        {
          label: "Open Technician Mobile",
          description: "View and update the maintenance work assigned to you.",
          action: function () { frappe.set_route("technician-mobile"); }
        },
        {
          label: "Open Facility Portal",
          description: "Submit and track your own facility requests.",
          action: function () { window.location.assign("/facility-portal"); }
        }
      ];
    } else if (roles.includes("Employee")) {
      launchers = [
        {
          label: "Open Facility Portal",
          description: "Submit and track your own facility requests.",
          action: function () { window.location.assign("/facility-portal"); }
        }
      ];
    }

    if (!launchers.length || document.getElementById("cafm-welcome-launcher")) return;

    const target = $(".layout-main-section").first().length
      ? $(".layout-main-section").first()
      : $(".page-body").first();
    if (!target.length) return;

    const card = $('<section id="cafm-welcome-launcher" class="cafm-welcome-launcher"></section>');
    launchers.forEach(function (launcher) {
      const launcher_card = $('<article class="cafm-welcome-launcher-card"><span>CAFM</span><h2></h2><p></p><button class="btn btn-primary"></button></article>');
      launcher_card.find("h2").text(launcher.label);
      launcher_card.find("p").text(launcher.description);
      launcher_card.find("button").text(launcher.label).on("click", launcher.action);
      launcher_card.appendTo(card);
    });
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
  frappe.dom.set_style(".cafm-welcome-launcher{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;max-width:760px;margin:24px auto}.cafm-welcome-launcher-card{padding:28px;border:1px solid #d7e6f1;border-radius:16px;background:linear-gradient(135deg,#f5fbff,#ffffff);text-align:center;box-shadow:0 7px 20px rgba(24,76,112,.07)}.cafm-welcome-launcher-card span{display:inline-block;padding:4px 9px;border-radius:99px;background:#e4f3fd;color:#1c679d;font-size:11px;font-weight:800;letter-spacing:.5px}.cafm-welcome-launcher-card h2{margin:13px 0 7px;color:#174f80;font-size:25px}.cafm-welcome-launcher-card p{margin:0 auto 19px;max-width:400px;color:#587187}.cafm-welcome-launcher-card .btn{padding:10px 17px;background:#0f5a97;border-color:#0f5a97}");
})();