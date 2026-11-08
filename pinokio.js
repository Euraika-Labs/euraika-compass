module.exports = {
  version: "8.0.0",
  title: "Euraika Compass",
  description: "Personal, neutral theological research: sources, images and transcript revisions.",
  icon: "icon.svg",
  menu: async (kernel, info) => {
    const installed = info.exists("app/backend/env") && info.exists("app/frontend/dist/index.html");
    for (const [script, label] of [["install.js", "Installing"], ["update.js", "Updating"], ["reset.js", "Resetting dependencies"]]) {
      if (info.running(script)) return [{ default: true, icon: "fa-solid fa-terminal", text: label, href: script }];
    }
    if (info.running("start.js")) {
      const local = info.local("start.js");
      return [
        ...(local?.url ? [{ default: true, icon: "fa-solid fa-compass", text: "Open Web UI", href: local.url }] : []),
        { default: !local?.url, icon: "fa-solid fa-terminal", text: "Terminal / Stop", href: "start.js" },
      ];
    }
    if (!installed) return [{ default: true, icon: "fa-solid fa-download", text: "Install", href: "install.js" }];
    return [
      { default: true, icon: "fa-solid fa-play", text: "Start", href: "start.js" },
      { icon: "fa-solid fa-rotate", text: "Update", href: "update.js" },
      { icon: "fa-solid fa-download", text: "Repair install", href: "install.js" },
      { icon: "fa-solid fa-broom", text: "Reset dependencies (keeps research)", href: "reset.js" },
    ];
  },
};
