const toggleStyles = `
input[type="checkbox"] {
  height: 0;
  width: 0;
  visibility: hidden;
  position: absolute;
}

label {
  --module-width: 36px;
  --module-height: 20px;
  --module-border: 2px;
  --color-bg: var(--color-bg-light, #444);
  --color-action: var(--color-action-light, #AAF);

  cursor: pointer;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: calc(1rem / 2);
  user-select: none;
  font-size: 80%;
  flex-wrap: wrap;
}

input[type="checkbox"]:checked + label {
  --color-bg: var(--color-bg-dark, #ccc);
  --color-action: var(--color-action-dark, #44F)
}

.control {
  display: block;
  position: relative;
  width: var(--module-width);
  height: var(--module-height);
  background: var(--color-bg);
  border-radius: var(--module-height);
  outline-offset: 0;
  transition: outline-offset .2s;
}

.control:focus {
  outline: var(--module-border) solid var(--color-action);
  outline-offset: var(--module-border);
}

.control::after {
  --control-dimension: calc(var(--module-height) - (var(--module-border) * 2));

  content: '';
  position: absolute;
  top: var(--module-border);
  left: var(--module-border);
  width: var(--control-dimension);
  height: var(--control-dimension);
  background: var(--color-action);
  border-radius: var(--control-dimension);
  transition: 0.2s;
}

input[type="checkbox"]:checked + label span.control::after {
  left: calc(var(--module-width) - var(--module-border));
  transform: translateX(-100%);
}

label:active span.control::after {
  width: calc(var(--module-height) + var(--module-border));
}
`;

class ThemeSwitcher extends HTMLElement {
  constructor() {
    super();

    // Create all elements
    const inputEl = document.createElement("input");
    const labelEl = document.createElement("label");
    const controlEl = document.createElement("span");
    const textEl = document.createElement("span");
    const emptyEl = document.createElement("span");

    // Get translations
    const choices = {
      dark: this.hasAttribute("light")
        ? this.getAttribute("light")
        : "Switch to light mode",
      light: this.hasAttribute("dark")
        ? this.getAttribute("dark")
        : "Switch to dark mode"
    };

    inputEl.checked = window.theme === "dark";
    textEl.textContent = choices[window.theme];

    // Checkbox Change Event
    inputEl.addEventListener("change", () => {
      toggleTheme();
      inputEl.checked = window.theme === "dark";
      textEl.textContent = choices[window.theme];
    });
    controlEl.addEventListener("keydown", event => {
      if ([" ", "Enter"].includes(event.key)) {
        event.preventDefault();
        toggleTheme();
        inputEl.checked = window.theme === "dark";
        textEl.textContent = choices[window.theme];
      };
    })

    // Add attributes
    inputEl.type = "checkbox";
    inputEl.id = "theme-switch";
    labelEl.setAttribute("for", inputEl.id);
    controlEl.classList.add("control");
    textEl.classList.add("text");
    controlEl.setAttribute("tabindex", 0);

    // Append it to the shadow root
    this.appendChild(inputEl);
    this.appendChild(labelEl);
    labelEl.appendChild(controlEl);
    labelEl.appendChild(textEl);
    textEl.appendChild(emptyEl);

    // Style
    const styleEl = document.createElement("style");
    styleEl.textContent = toggleStyles;
    this.appendChild(styleEl);
  }
}

// Define the new element
customElements.define("theme-switch", ThemeSwitcher);

// Scroll today's table to current time column

var scrollEl = document.querySelector("th.cell_past ~ th:not(.cell_past)");

var scrollElWrapper = scrollEl?.closest(".table-container");
scrollElWrapper && scrollElWrapper.scroll({
    left: scrollEl.offsetLeft - scrollElWrapper.offsetWidth / 2,
    behavior: 'smooth'
});

// Location form utilities

var locationForm = document.getElementById("location-form");
var locationSubmit = locationForm.querySelector("button[type='submit']");
var locationReset = locationForm.querySelector("#location-reset");
var locationInput = locationForm.querySelector("#location-input");
var locationsList = locationForm.querySelector("#locations-list");

locationReset.addEventListener("click", (e) => {
    locationInput.value = "";
    locationInput.focus();
});

locationInput.addEventListener("input", (event) => {
    const value = event.target.value;

    locationForm.querySelector("input[type='hidden'][name='latitude']").value = "";
    locationForm.querySelector("input[type='hidden'][name='longitude']").value = "";
    locationSubmit?.setAttribute("disabled", true);

    if(event.inputType == "insertReplacementText" || event.inputType == null) {
        const options = [...locationsList.options];

        const selected_option = options.find(o => o.value === value);

        locationForm.querySelector("input[type='hidden'][name='latitude']").value = selected_option.dataset.latitude
        locationForm.querySelector("input[type='hidden'][name='longitude']").value = selected_option.dataset.longitude
        locationSubmit?.removeAttribute("disabled");
    }
});

locationInput.addEventListener("input", (e) => {
    if (!window.fetch) return;

    window.fetch("/location?search=" + e.target.value)
    .then(function (r) {
        return r.text();
    })
    .then(function(data) {
        console.log(data);
        locationsList.innerHTML = data;
    });
});
