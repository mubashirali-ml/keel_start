/* Theme bootstrap (ADR-0019, ADR-0033): runs before first paint from a static file, so the
   page never flashes the wrong theme and the CSP needs no inline scripts.
   Stored choice: localStorage "launch.theme" = "light" | "dark" | "system" (default). */
(function () {
  var choice = "system";
  try {
    var stored = window.localStorage.getItem("launch.theme");
    if (stored === "light" || stored === "dark" || stored === "system") choice = stored;
  } catch (e) {
    /* storage blocked: follow the system */
  }
  var dark =
    choice === "dark" ||
    (choice === "system" && !!window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  var root = document.documentElement;
  if (dark) root.classList.add("dark");
  else root.classList.remove("dark");
  root.style.colorScheme = dark ? "dark" : "light";
})();
