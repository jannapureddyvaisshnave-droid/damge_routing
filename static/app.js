// CargoPath — frontend helpers

function swapCities() {
  const from = document.getElementById("quickFrom");
  const to   = document.getElementById("quickTo");
  if (!from || !to) return;
  const tmp = from.value;
  from.value = to.value;
  to.value = tmp;
}

// Mobile nav toggle
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("navToggle");
  const links  = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }
});