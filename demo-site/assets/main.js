// Acme Widgets main script - intentionally unoptimized.
(function () {
  "use strict";
  var config = {
    siteName: "Acme Widgets",
    analytics: "gtag",
    pixel: "fbevents",
    social: "social-widget"
  };
  function logEvent(name) {
    console.log("[acme] event", name);
  }
  logEvent("init");
  window.AcmeWidgets = { config: config, logEvent: logEvent };
})();
