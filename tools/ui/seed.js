/* For screenshots of member pages: a signed-in HR admin of a company with sample data (tools/ui/hrseed.js).
   Resolves to window.SEED (ids for the pages that need one). */
(async function () {
  try { return await window.hrSeed('Sam Rivera'); } catch (e) { return { error: String(e && e.message || e) }; }
})();
