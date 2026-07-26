/*
 * Add Gear form: show only the type-specific fields for the selected gear
 * type, and disable the hidden inputs so their (shared) field names are not
 * submitted.
 */

(function () {
  const typeSelect = document.getElementById("gear_type");
  if (!typeSelect) return;

  function updateSections() {
    const selected = typeSelect.value;
    document.querySelectorAll("[data-gear-section]").forEach(function (section) {
      const active = section.dataset.gearSection === selected;
      section.hidden = !active;
      section.querySelectorAll("input, select").forEach(function (field) {
        field.disabled = !active;
      });
    });
  }

  typeSelect.addEventListener("change", updateSections);
  updateSections();
})();
